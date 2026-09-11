"""Property tests for `apps/users/tokens.py` hashing (design.md DD1,
Testing Strategy § "Token hashing").

Pure hypothesis — no `django_db` needed for the hashing property itself;
`resolve_token`/`issue_token` behavior against the DB is covered by the
services-layer RED tests instead.
"""
from hypothesis import given, settings
from hypothesis import strategies as st

from apps.users.tokens import hash_token

_raw_tokens = st.text(
    alphabet=st.characters(min_codepoint=33, max_codepoint=126), min_size=16, max_size=64
)


@settings(max_examples=100)
@given(raw=_raw_tokens)
def test_hash_token_never_equals_its_raw_input(raw: str):
    assert hash_token(raw) != raw


@settings(max_examples=100)
@given(raw=_raw_tokens)
def test_hash_token_is_deterministic_and_64_hex_chars(raw: str):
    digest = hash_token(raw)

    assert hash_token(raw) == digest
    assert len(digest) == 64
    assert all(c in "0123456789abcdef" for c in digest)


@settings(max_examples=200)
@given(pair=st.tuples(_raw_tokens, _raw_tokens).filter(lambda p: p[0] != p[1]))
def test_distinct_raw_tokens_hash_to_distinct_values(pair: tuple[str, str]):
    raw_a, raw_b = pair
    assert hash_token(raw_a) != hash_token(raw_b)
