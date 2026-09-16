"""Redis-backed ephemeral node locks (design.md DD1, DD2, DD3, DD10).

A deliberately separate lock domain from Postgres row locking (DD5): this
module never touches the database, and a held claim never blocks, delays,
or is consulted by any `UmlCommand`/`submit_command` call. The client is a
lazy module-level **sync** `redis.Redis` built from `settings.REDIS_HOST`/
`REDIS_PORT` — the same coordinate the channel layer already depends on
(`config/settings.py`) — so no new env var is introduced.

Key: `uml-lock:{doc_id}:{class_id}`. Value: `f"{token}|{label}"`, where
`token` is a per-**connection** `uuid4().hex` (DD2) — never a routable
`channel_name`. Release and refresh are registered Lua scripts (DD3):
atomic owner-only compare-and-delete / compare-and-expire, so a plain
"GET then DEL/PEXPIRE" race between two connections is impossible.
"""
from typing import Any

import redis
from django.conf import settings

LOCK_TTL_MS = 10_000

_RELEASE_LUA = """
local current = redis.call('GET', KEYS[1])
if current and string.match(current, '^([^|]*)|') == ARGV[1] then
  return redis.call('DEL', KEYS[1])
else
  return 0
end
"""

_REFRESH_LUA = """
local current = redis.call('GET', KEYS[1])
if current and string.match(current, '^([^|]*)|') == ARGV[1] then
  return redis.call('PEXPIRE', KEYS[1], ARGV[2])
else
  return 0
end
"""

_client: "redis.Redis | None" = None
_release_script: Any = None
_refresh_script: Any = None


def _get_client() -> "redis.Redis":
    global _client, _release_script, _refresh_script
    if _client is None:
        _client = redis.Redis(
            host=settings.REDIS_HOST, port=settings.REDIS_PORT, decode_responses=True
        )
        _release_script = _client.register_script(_RELEASE_LUA)
        _refresh_script = _client.register_script(_REFRESH_LUA)
    return _client


def key(doc_id: object, class_id: str) -> str:
    return f"uml-lock:{doc_id}:{class_id}"


def claim(*, doc_id: object, class_id: str, token: str, label: str) -> tuple[bool, str | None]:
    """`SET NX PX` (DD2) — the single atomic operation that resolves
    near-simultaneous claims to exactly one winner server-side. Returns
    `(True, None)` on success or `(False, current_owner_label)` when the
    node is already held.
    """
    client = _get_client()
    lock_key = key(doc_id, class_id)
    ok = client.set(lock_key, f"{token}|{label}", nx=True, px=LOCK_TTL_MS)
    if ok:
        return True, None
    current = client.get(lock_key)
    if current is None:
        # Expired between the failed SET and this GET: unheld from the
        # caller's perspective, not a phantom owner.
        return False, None
    _current_token, _, current_label = current.partition("|")
    return False, current_label


def refresh(*, doc_id: object, class_id: str, token: str) -> bool:
    """Owner-only `PEXPIRE` (DD3). Doubles as the per-frame authorization
    check: a live-position frame is broadcast only when this returns
    `True`.
    """
    _get_client()
    result = _refresh_script(keys=[key(doc_id, class_id)], args=[token, LOCK_TTL_MS])
    return bool(result)


def release(*, doc_id: object, class_id: str, token: str) -> bool:
    """Owner-only compare-and-delete (DD3)."""
    _get_client()
    result = _release_script(keys=[key(doc_id, class_id)], args=[token])
    return bool(result)


def snapshot(*, doc_id: object) -> list[tuple[str, str, str]]:
    """`SCAN MATCH` (DD10 — never `KEYS`, which blocks the whole server)
    over this document's lock prefix. Returns `(class_id, token, label)`
    triples for every currently held lock.
    """
    client = _get_client()
    prefix = f"uml-lock:{doc_id}:"
    entries: list[tuple[str, str, str]] = []
    cursor = 0
    while True:
        cursor, found_keys = client.scan(cursor=cursor, match=f"{prefix}*", count=100)
        for found_key in found_keys:
            value = client.get(found_key)
            if value is None:
                continue
            class_id = found_key[len(prefix) :]
            token, _, label = value.partition("|")
            entries.append((class_id, token, label))
        if cursor == 0:
            break
    return entries
