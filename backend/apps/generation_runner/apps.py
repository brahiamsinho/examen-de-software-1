"""Django app registration shell for the generated-project runner (design.md DD75).

This app has no `models.py` and no `migrations/`. It splits into a pure
part (`domain/` errors and Protocols, `writer/` filesystem writer) that
never imports `apps.spring_generator`, and glue outside that part
(`cli.py`, `runner_image.py`, `samples/`) that may import the generator
because nothing imports the glue. Registration mirrors
`apps.spring_generator` one step later in the same pipeline.
"""
from django.apps import AppConfig


class GenerationRunnerConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.generation_runner"
    label = "generation_runner"
