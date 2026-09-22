"""HTTP router exposing derived join tables for a document's current model.

Thin, like `apps.generation_export.api`: resolve membership -> load the
document -> call `map_to_relational` -> filter and serialize. Read-only, any
org member may fetch it. The diagram canvas draws these as a visual hint
next to a both-ends-many association (design.md DD177): a many-to-many
association needs an intermediate table when the backend is generated, and
the user asked to see that table on the diagram itself instead of only
discovering it after generating. Reusing `map_to_relational` — the exact
function `apps.generation_export`/`apps.spring_generator` already use to
build the real backend — is what keeps the drawn table's name and columns
from ever drifting out of sync with what actually gets generated; a
frontend-side reimplementation of the naming rules would not have that
guarantee.
"""
from uuid import UUID

from django.http import HttpRequest
from ninja import Path, Router, Schema
from ninja.security import django_auth

from apps.organizations.permissions import resolve_membership
from apps.relational_mapping.mapping.errors import UnmappableModelError
from apps.relational_mapping.mapping.mapper import map_to_relational
from apps.uml_documents import services

relational_router = Router(auth=django_auth)


class JoinTableOut(Schema):
    relationship_id: str
    table_name: str
    columns: list[str]


@relational_router.get("/{doc_id}/join-tables", response={200: list[JoinTableOut]})
def join_tables_view(request: HttpRequest, org_slug: Path[str], doc_id: UUID):
    membership = resolve_membership(request, org_slug)  # any member reads
    document = services.get_document(organization=membership.organization, doc_id=doc_id)

    try:
        relational = map_to_relational(document.model)
    except UnmappableModelError:
        # An in-progress edit can leave the model unmappable for a moment
        # (e.g. a dangling relationship); the diagram itself already shows
        # that problem elsewhere, so this hint just goes quiet instead of
        # erroring the canvas.
        return []

    return [
        JoinTableOut(
            relationship_id=str(table.foreign_keys[0].source_relationship_id),
            table_name=table.name,
            columns=[column.name for column in table.columns],
        )
        # A join table is the one Stage-4 shape with no owning class
        # (design.md DD16/DD21): `source_class_ids` empty, exactly the two
        # FKs `_build_join_table` always emits.
        for table in relational.tables
        if not table.source_class_ids and len(table.foreign_keys) == 2
    ]
