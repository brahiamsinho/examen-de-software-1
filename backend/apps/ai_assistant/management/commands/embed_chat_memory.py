"""Gives the chat's semantic memory a vector for every message written before it existed."""
from django.core.management.base import BaseCommand, CommandError

from apps.ai_assistant import memory
from apps.ai_assistant.llm_provider import get_active_llm_client


class Command(BaseCommand):
    help = "Embeds the chat messages that have no vector yet, so the AI can recall them."

    def handle(self, *args, **options):
        try:
            done = memory.backfill(get_active_llm_client())
        except memory.EmbeddingsUnavailable as error:
            raise CommandError(str(error)) from error
        self.stdout.write(self.style.SUCCESS(f"Embedded {done} message(s)."))