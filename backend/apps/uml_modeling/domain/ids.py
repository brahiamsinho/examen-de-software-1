"""Element identity for the canonical UML domain.

Ids are plain strings (uuid4 hex) rather than `uuid.UUID` or a dataclass
wrapper: strings serialize to JSON/XMI with no adapter, and `NewType`
gives static distinctness at zero runtime cost. Ids double as the
diagnostic `path` alphabet (see `validation/diagnostics.py`).
"""
import uuid
from typing import NewType

ElementId = NewType("ElementId", str)


def new_id() -> ElementId:
    """Generate a new random element id (uuid4 hex, no dashes)."""
    return ElementId(uuid.uuid4().hex)
