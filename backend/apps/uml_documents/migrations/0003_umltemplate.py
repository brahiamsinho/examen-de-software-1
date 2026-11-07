from django.conf import settings
import django.db.models.manager
from django.db import migrations, models
import django.db.models.deletion
import uuid


class Migration(migrations.Migration):
    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("organizations", "0002_initial"),
        ("uml_documents", "0002_umlversion"),
    ]

    operations = [
        migrations.CreateModel(
            name="UmlTemplate",
            fields=[
                ("organization", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="%(class)ss", to="organizations.organization")),
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("name", models.CharField(max_length=255)),
                ("snapshot", models.JSONField(default=dict)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("created_by", models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="+", to=settings.AUTH_USER_MODEL)),
                ("source_document", models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="templates", to="uml_documents.umldocument")),
            ],
            options={"base_manager_name": "all_objects"},
            managers=[
                ("objects", django.db.models.manager.Manager()),
                ("all_objects", django.db.models.manager.Manager()),
            ],
        ),
        migrations.AddIndex(model_name="umltemplate", index=models.Index(fields=["organization", "name"], name="uml_documen_organiz_5bd724_idx")),
    ]
