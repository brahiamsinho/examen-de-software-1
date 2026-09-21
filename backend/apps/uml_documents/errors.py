"""Domain errors for the uml_documents API layer.

The outer `{type, payload}` command envelope is already rejected with a
clean 422 by django-ninja/pydantic's discriminated-union validation before
reaching `services.py`. This module covers the *inner* payload shapes
(`attribute.type`, a relationship end's `multiplicity` string) that the
loosely-typed `str | dict` schema fields defer to manual decoding in
`services.py`/`codec.py` — a malformed inner shape must surface as a 422,
not an unhandled 500.
"""


class InvalidCommandPayloadError(ValueError):
    """A command payload's inner shape could not be converted to a domain object."""


class DocumentNotEmptyError(Exception):
    """The target document already has classes or relationships, so its content cannot be replaced."""
