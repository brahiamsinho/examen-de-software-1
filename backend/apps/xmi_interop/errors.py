"""Domain errors of the XMI import. `code` is the stable API error code."""


class XmiError(Exception):
    code = "invalid_xmi"


class InvalidXmiError(XmiError):
    """The bytes are not usable XML (malformed, too large, or a forbidden construct)."""

    code = "invalid_xmi"


class UnsupportedXmiError(XmiError):
    """Well-formed XML that is not an XMI class model we can read (or has no classes)."""

    code = "unsupported_xmi"
