import django.db.models.deletion
import django.db.models.manager
import uuid

from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("organizations", "0002_initial"),
        ("uml_documents", "0001_initial"),
        ("backend_deployments", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="RemoteDeploymentDestination",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("name", models.CharField(max_length=120)),
                ("destination_type", models.CharField(default="vm_containers", max_length=32)),
                ("environment", models.CharField(choices=[("development", "Development"), ("testing", "Testing"), ("production", "Production")], max_length=16)),
                ("managed_config_id", models.CharField(max_length=120)),
                ("connectivity_config_ref", models.CharField(max_length=120)),
                ("capabilities", models.JSONField(default=list)),
                ("enabled", models.BooleanField(default=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("organization", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="%(class)ss", to="organizations.organization")),
            ],
            options={"base_manager_name": "all_objects"},
            managers=[("objects", django.db.models.manager.Manager()), ("all_objects", django.db.models.manager.Manager())],
        ),
        migrations.CreateModel(
            name="RemoteDeploymentRequest",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("action", models.CharField(default="deploy", max_length=16)),
                ("status", models.CharField(choices=[("DRAFT", "Draft"), ("VALIDATED", "Validated"), ("AWAITING_CONFIRMATION", "Awaiting Confirmation"), ("AUTHORIZED", "Authorized"), ("QUEUED", "Queued"), ("DEPLOYING", "Deploying"), ("RUNNING", "Running"), ("FAILED", "Failed"), ("STOPPED", "Stopped"), ("CANCELLED", "Cancelled")], default="DRAFT", max_length=24)),
                ("document_revision", models.PositiveIntegerField()), ("artifact_sha256", models.CharField(max_length=64)), ("validation", models.JSONField(default=dict)), ("confirmation_digest", models.CharField(blank=True, default="", max_length=64)), ("confirmation_expires_at", models.DateTimeField(blank=True, null=True)), ("confirmation_used_at", models.DateTimeField(blank=True, null=True)), ("correlation_id", models.UUIDField(default=uuid.uuid4, editable=False)), ("error_code", models.CharField(blank=True, default="", max_length=64)), ("error_message", models.TextField(blank=True, default="")), ("created_at", models.DateTimeField(auto_now_add=True)), ("updated_at", models.DateTimeField(auto_now=True)),
                ("created_by", models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="+", to=settings.AUTH_USER_MODEL)), ("destination", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="requests", to="backend_deployments.remotedeploymentdestination")), ("document", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="remote_deployment_requests", to="uml_documents.umldocument")), ("organization", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="%(class)ss", to="organizations.organization")),
            ], options={"base_manager_name": "all_objects"},
            managers=[("objects", django.db.models.manager.Manager()), ("all_objects", django.db.models.manager.Manager())],
        ),
        migrations.CreateModel(
            name="RemoteDeploymentEvent",
            fields=[
                ("id", models.BigAutoField(primary_key=True, serialize=False)), ("action", models.CharField(max_length=32)), ("previous_status", models.CharField(blank=True, default="", max_length=24)), ("new_status", models.CharField(max_length=24)), ("result", models.CharField(max_length=16)), ("error_code", models.CharField(blank=True, default="", max_length=64)), ("message", models.CharField(blank=True, default="", max_length=500)), ("correlation_id", models.UUIDField()), ("created_at", models.DateTimeField(auto_now_add=True)),
                ("actor", models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="+", to=settings.AUTH_USER_MODEL)), ("organization", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="%(class)ss", to="organizations.organization")), ("request", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="events", to="backend_deployments.remotedeploymentrequest")),
            ], options={"base_manager_name": "all_objects", "ordering": ["id"]},
            managers=[("objects", django.db.models.manager.Manager()), ("all_objects", django.db.models.manager.Manager())],
        ),
        migrations.AddConstraint(model_name="remotedeploymentdestination", constraint=models.UniqueConstraint(fields=("organization", "managed_config_id"), name="remote_destination_org_config_uniq")),
        migrations.AddIndex(model_name="remotedeploymentdestination", index=models.Index(fields=["organization", "enabled"], name="remote_dest_org_enabled_idx")),
        migrations.AddIndex(model_name="remotedeploymentrequest", index=models.Index(fields=["organization", "document", "status"], name="remote_req_org_doc_status_idx")),
        migrations.AddIndex(model_name="remotedeploymentevent", index=models.Index(fields=["organization", "request", "id"], name="remote_event_org_req_id_idx")),
    ]
