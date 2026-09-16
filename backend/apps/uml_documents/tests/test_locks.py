"""Redis-backed ephemeral node lock module (design.md DD1-DD3, DD10).

Exercises a real Redis instance via `settings.REDIS_HOST`/`REDIS_PORT`
(the same coordinate the channel layer already depends on) rather than a
fake — Redis is already deployed and healthchecked in this project's
`docker-compose.yml` (design.md's Migration/Rollout section), and the
atomicity these tests assert (Lua compare-and-delete/compare-and-expire)
cannot be proven against an in-memory stand-in. Each test uses a fresh
`uuid4` doc id and class id so tests never collide on a shared key, and
locks self-expire on their 10s TTL even without explicit cleanup.
"""
import time
import uuid
from unittest.mock import patch

from apps.uml_documents import locks


def _ids() -> tuple[uuid.UUID, str]:
    return uuid.uuid4(), f"c-{uuid.uuid4().hex[:8]}"


def test_claim_on_unheld_key_succeeds():
    doc_id, class_id = _ids()

    ok, owner_label = locks.claim(doc_id=doc_id, class_id=class_id, token="tok-a", label="Ana")

    assert ok is True
    assert owner_label is None


def test_claim_twice_returns_false_and_first_owners_label():
    doc_id, class_id = _ids()
    locks.claim(doc_id=doc_id, class_id=class_id, token="tok-a", label="Ana")

    ok, owner_label = locks.claim(doc_id=doc_id, class_id=class_id, token="tok-b", label="Bruno")

    assert ok is False
    assert owner_label == "Ana"


def test_release_with_foreign_token_returns_false_and_leaves_the_key():
    doc_id, class_id = _ids()
    locks.claim(doc_id=doc_id, class_id=class_id, token="tok-a", label="Ana")

    released = locks.release(doc_id=doc_id, class_id=class_id, token="tok-b")

    assert released is False
    # The key is still held by tok-a: a third party still cannot claim it.
    ok, owner_label = locks.claim(doc_id=doc_id, class_id=class_id, token="tok-c", label="Carla")
    assert ok is False
    assert owner_label == "Ana"


def test_refresh_with_foreign_token_returns_false():
    doc_id, class_id = _ids()
    locks.claim(doc_id=doc_id, class_id=class_id, token="tok-a", label="Ana")

    refreshed = locks.refresh(doc_id=doc_id, class_id=class_id, token="tok-b")

    assert refreshed is False


def test_refresh_with_owner_token_returns_true():
    doc_id, class_id = _ids()
    locks.claim(doc_id=doc_id, class_id=class_id, token="tok-a", label="Ana")

    refreshed = locks.refresh(doc_id=doc_id, class_id=class_id, token="tok-a")

    assert refreshed is True


def test_release_then_reclaim_succeeds():
    doc_id, class_id = _ids()
    locks.claim(doc_id=doc_id, class_id=class_id, token="tok-a", label="Ana")

    released = locks.release(doc_id=doc_id, class_id=class_id, token="tok-a")
    assert released is True

    ok, owner_label = locks.claim(doc_id=doc_id, class_id=class_id, token="tok-b", label="Bruno")
    assert ok is True
    assert owner_label is None


def test_snapshot_returns_class_id_token_label_triples_for_held_locks():
    doc_id, class_id = _ids()
    locks.claim(doc_id=doc_id, class_id=class_id, token="tok-a", label="Ana")

    entries = locks.snapshot(doc_id=doc_id)

    assert (class_id, "tok-a", "Ana") in entries


def test_snapshot_is_scoped_to_its_own_document():
    doc_id_a, class_id_a = _ids()
    doc_id_b, class_id_b = _ids()
    locks.claim(doc_id=doc_id_a, class_id=class_id_a, token="tok-a", label="Ana")
    locks.claim(doc_id=doc_id_b, class_id=class_id_b, token="tok-b", label="Bruno")

    entries_a = locks.snapshot(doc_id=doc_id_a)

    class_ids_a = {entry[0] for entry in entries_a}
    assert class_id_a in class_ids_a
    assert class_id_b not in class_ids_a


def test_claim_sets_a_ttl_close_to_lock_ttl_ms():
    doc_id, class_id = _ids()

    ok, _owner_label = locks.claim(doc_id=doc_id, class_id=class_id, token="tok-a", label="Ana")
    assert ok is True

    client = locks._get_client()
    pttl = client.pttl(locks.key(doc_id, class_id))

    # `PTTL` returns -1 for "no TTL" and -2 for "missing key"; a real claim
    # must carry a positive millisecond TTL no larger than the configured
    # `LOCK_TTL_MS` (design.md DD2 — `SET NX PX`).
    assert 0 < pttl <= locks.LOCK_TTL_MS


def test_abandoned_claim_expires_via_ttl_and_becomes_claimable_again():
    doc_id, class_id = _ids()
    short_ttl_ms = 50

    # Patch the module constant instead of `locks.py` itself: `claim()`
    # reads `LOCK_TTL_MS` from module globals on every call, so this swaps
    # the effective TTL for this test only without touching production code.
    with patch.object(locks, "LOCK_TTL_MS", short_ttl_ms):
        ok, _owner_label = locks.claim(
            doc_id=doc_id, class_id=class_id, token="tok-a", label="Ana"
        )
        assert ok is True

        # A second claim before expiry is still rejected: the lock is held.
        blocked, owner_label = locks.claim(
            doc_id=doc_id, class_id=class_id, token="tok-b", label="Bruno"
        )
        assert blocked is False
        assert owner_label == "Ana"

    # Never refreshed: sleep past the short TTL (well beyond it to absorb
    # scheduling jitter) so the key self-expires in Redis.
    time.sleep(short_ttl_ms / 1000 * 3)

    reclaimed, owner_label = locks.claim(
        doc_id=doc_id, class_id=class_id, token="tok-c", label="Carla"
    )

    assert reclaimed is True
    assert owner_label is None
