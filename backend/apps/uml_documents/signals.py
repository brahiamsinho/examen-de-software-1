"""Signals other apps may subscribe to, so `uml_documents` never imports them."""
from django.dispatch import Signal

# Sent after a diagram change is committed. kwargs: `document` (the domain document).
document_changed = Signal()
