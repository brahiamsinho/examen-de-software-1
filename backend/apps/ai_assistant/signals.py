"""Signals other apps may subscribe to, so `ai_assistant` never imports them."""
from django.dispatch import Signal

# Sent after a new AI draft is committed. kwargs: `organization`, `document`, `requested_by_id`.
proposal_created = Signal()
