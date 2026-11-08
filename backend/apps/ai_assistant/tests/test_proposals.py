"""Service tests for AI board proposals (issue #15): the AI suggests changes
as drafts that never touch the document until a developer approves them."""
from unittest import mock

import pytest
from django.http import Http404
from django.utils import timezone

from apps.ai_assistant import proposals
from apps.ai_assistant.gemini_client import GeminiFunctionCall
from apps.organizations.tests.factories import make_org_with_roles
from apps.uml_documents import services


class _FakeClient:
    def __init__(self, calls):
        self._calls = calls
        self.transcripts: list[str] = []

    def generate_function_calls(self, *, system_instruction, transcript, tools):
        self.transcripts.append(transcript)
        return self._calls


def _document(organization, owner):
    return services.create_document(
        organization=organization, owner_id=str(owner.id), name="Board", now=timezone.now()
    )


def _add_class(organization, doc_id, name="Persona"):
    return services.submit_commands(
        organization=organization,
        doc_id=doc_id,
        commands_to_apply=[services.command_from_payload(_payload(name))],
        now=timezone.now(),
    )


def _payload(name):
    from apps.uml_documents import schemas

    return schemas.AddClassIn(type="AddClass", class_id=f"id-{name}", name=name)


def _suggest(organization, doc_id, user, calls=None, prompt="What is missing?"):
    calls = calls if calls is not None else [GeminiFunctionCall(name="add_class", args={"name": "Pedido"})]
    return proposals.create_proposal(
        organization=organization,
        doc_id=doc_id,
        requested_by=user,
        prompt=prompt,
        gemini=_FakeClient(calls),
    )


@pytest.mark.django_db
class TestCreateProposal:
    def test_the_proposal_is_a_pending_draft_and_the_document_is_untouched(self):
        organization, owner, *_ = make_org_with_roles()
        document = _document(organization, owner)

        proposal = _suggest(organization, document.id, owner)

        assert proposal.status == "pending"
        assert proposal.base_revision == document.revision
        assert proposal.requested_by == owner
        assert proposal.changes[0]["ok"] is True
        assert "Pedido" in proposal.changes[0]["message"]
        after = services.get_document(organization=organization, doc_id=document.id)
        assert after.revision == document.revision
        assert after.model.classes == ()

    def test_the_model_sees_the_diagram_and_the_request(self):
        organization, owner, *_ = make_org_with_roles()
        document = _document(organization, owner)
        client = _FakeClient([GeminiFunctionCall(name="add_class", args={"name": "Pedido"})])

        proposals.create_proposal(
            organization=organization, doc_id=document.id, requested_by=owner, prompt="Add orders", gemini=client
        )

        assert "Add orders" in client.transcripts[0]
        assert "empty" in client.transcripts[0]

    def test_an_answer_with_no_suggestions_is_rejected_with_a_clear_message(self):
        organization, owner, *_ = make_org_with_roles()
        document = _document(organization, owner)

        with pytest.raises(proposals.NoSuggestionsError):
            _suggest(organization, document.id, owner, calls=[])

    def test_a_foreign_organization_cannot_propose_on_the_document(self):
        organization, owner, *_ = make_org_with_roles()
        other_organization, other_owner, *_ = make_org_with_roles()
        document = _document(organization, owner)

        with pytest.raises(Http404):
            _suggest(other_organization, document.id, other_owner)


@pytest.mark.django_db
class TestDecideProposal:
    def test_approving_applies_the_changes_and_records_who_decided(self):
        organization, owner, editor, *_ = make_org_with_roles()
        document = _document(organization, owner)
        proposal = _suggest(organization, document.id, owner)

        approved = proposals.approve_proposal(
            organization=organization, doc_id=document.id, proposal_id=proposal.id, decided_by=editor, now=timezone.now()
        )

        assert approved.status == "approved"
        assert approved.decided_by == editor
        assert approved.decided_at is not None
        after = services.get_document(organization=organization, doc_id=document.id)
        assert [c.name for c in after.model.classes] == ["Pedido"]
        assert after.revision == document.revision + 1

    def test_rejecting_leaves_the_document_unchanged(self):
        organization, owner, editor, *_ = make_org_with_roles()
        document = _document(organization, owner)
        proposal = _suggest(organization, document.id, owner)

        rejected = proposals.reject_proposal(
            organization=organization, doc_id=document.id, proposal_id=proposal.id, decided_by=editor, now=timezone.now()
        )

        assert rejected.status == "rejected"
        assert rejected.decided_by == editor
        after = services.get_document(organization=organization, doc_id=document.id)
        assert after.revision == document.revision and after.model.classes == ()

    def test_a_proposal_goes_stale_when_the_diagram_changes_and_cannot_be_approved(self):
        organization, owner, editor, *_ = make_org_with_roles()
        document = _document(organization, owner)
        proposal = _suggest(organization, document.id, owner)
        _add_class(organization, document.id, "Persona")

        with pytest.raises(proposals.StaleProposalError):
            proposals.approve_proposal(
                organization=organization, doc_id=document.id, proposal_id=proposal.id, decided_by=editor, now=timezone.now()
            )

        refreshed = proposals.get_proposal(organization=organization, doc_id=document.id, proposal_id=proposal.id)
        assert refreshed.status == "stale"
        after = services.get_document(organization=organization, doc_id=document.id)
        assert [c.name for c in after.model.classes] == ["Persona"]

    def test_a_decided_proposal_cannot_be_decided_again(self):
        organization, owner, editor, *_ = make_org_with_roles()
        document = _document(organization, owner)
        proposal = _suggest(organization, document.id, owner)
        proposals.reject_proposal(
            organization=organization, doc_id=document.id, proposal_id=proposal.id, decided_by=editor, now=timezone.now()
        )

        with pytest.raises(proposals.ProposalAlreadyDecidedError):
            proposals.approve_proposal(
                organization=organization, doc_id=document.id, proposal_id=proposal.id, decided_by=editor, now=timezone.now()
            )

    def test_a_proposal_with_unapplicable_changes_cannot_be_approved(self):
        organization, owner, editor, *_ = make_org_with_roles()
        document = _document(organization, owner)
        proposal = _suggest(
            organization,
            document.id,
            owner,
            calls=[GeminiFunctionCall(name="rename_class", args={"class_name": "Ghost", "new_name": "X"})],
        )

        assert proposal.changes[0]["ok"] is False
        with pytest.raises(proposals.UnapplicableProposalError):
            proposals.approve_proposal(
                organization=organization, doc_id=document.id, proposal_id=proposal.id, decided_by=editor, now=timezone.now()
            )
        assert (
            services.get_document(organization=organization, doc_id=document.id).revision == document.revision
        )

    def test_another_organization_cannot_read_or_decide_the_proposal(self):
        organization, owner, *_ = make_org_with_roles()
        other_organization, other_owner, *_ = make_org_with_roles()
        document = _document(organization, owner)
        proposal = _suggest(organization, document.id, owner)

        with pytest.raises(Http404):
            proposals.approve_proposal(
                organization=other_organization,
                doc_id=document.id,
                proposal_id=proposal.id,
                decided_by=other_owner,
                now=timezone.now(),
            )
        with pytest.raises(Http404):
            proposals.list_proposals(organization=other_organization, doc_id=document.id)


def _suggestion(classes, relationships=()):
    return GeminiFunctionCall(
        name="suggest_uml_additions",
        args={"classes": list(classes), "relationships": list(relationships)},
    )


def _names(proposal):
    return [call["name"] for call in proposal.calls]


@pytest.mark.django_db
class TestStructuredSuggestions:
    def test_the_model_is_given_the_structured_tool_so_it_cannot_stop_at_class_names(self):
        organization, owner, *_ = make_org_with_roles()
        document = _document(organization, owner)
        seen = {}

        class _Recording(_FakeClient):
            def generate_function_calls(self, *, system_instruction, transcript, tools):
                seen["tools"] = [tool["name"] for tool in tools]
                return super().generate_function_calls(
                    system_instruction=system_instruction, transcript=transcript, tools=tools
                )

        proposals.create_proposal(
            organization=organization,
            doc_id=document.id,
            requested_by=owner,
            prompt="ideas",
            gemini=_Recording([_suggestion([{"name": "Pedido", "attributes": [], "operations": []}])]),
        )

        assert seen["tools"] == ["suggest_uml_additions"]

    def test_classes_arrive_with_their_attributes_operations_and_relationships(self):
        organization, owner, *_ = make_org_with_roles()
        document = _document(organization, owner)

        proposal = _suggest(
            organization,
            document.id,
            owner,
            calls=[
                _suggestion(
                    [
                        {
                            "name": "Pedido",
                            "attributes": [{"name": "total", "type": "Decimal"}],
                            "operations": [{"name": "calcular"}],
                        },
                        {"name": "Cliente", "attributes": [{"name": "email", "type": "String"}], "operations": []},
                    ],
                    [{"kind": "association", "source_class_name": "Cliente", "target_class_name": "Pedido"}],
                )
            ],
        )

        assert _names(proposal) == [
            "add_class",
            "add_class",
            "add_attribute",
            "add_operation",
            "add_attribute",
            "add_relationship",
        ]
        assert all(change["ok"] for change in proposal.changes)

    def test_existing_classes_and_relationships_are_never_duplicated(self):
        organization, owner, *_ = make_org_with_roles()
        document = _document(organization, owner)
        _add_class(organization, document.id, "Persona")

        proposal = _suggest(
            organization,
            document.id,
            owner,
            calls=[
                _suggestion(
                    [
                        {"name": "persona", "attributes": [{"name": "email", "type": "String"}], "operations": []},
                        {"name": "Pedido", "attributes": [], "operations": []},
                    ],
                    [{"kind": "association", "source_class_name": "Persona", "target_class_name": "Pedido"}],
                )
            ],
        )

        assert _names(proposal) == ["add_class", "add_attribute", "add_relationship"]
        assert proposal.calls[0]["args"] == {"name": "Pedido"}
        assert proposal.calls[1]["args"]["class_name"] == "persona"

    def test_an_attribute_the_class_already_has_is_not_proposed_again(self):
        organization, owner, *_ = make_org_with_roles()
        document = _document(organization, owner)
        _add_class(organization, document.id, "Persona")
        services.submit_commands(
            organization=organization,
            doc_id=document.id,
            commands_to_apply=[
                services.command_from_payload(
                    _attribute_payload("id-Persona", "email"),
                )
            ],
            now=timezone.now(),
        )

        with pytest.raises(proposals.NoSuggestionsError):
            _suggest(
                organization,
                document.id,
                owner,
                calls=[
                    _suggestion([{"name": "Persona", "attributes": [{"name": "Email", "type": "String"}], "operations": []}])
                ],
            )


def _link(source, target, source_multiplicity=None, target_multiplicity=None, kind="association"):
    relationship = {"kind": kind, "source_class_name": source, "target_class_name": target}
    if source_multiplicity:
        relationship["source_multiplicity"] = source_multiplicity
    if target_multiplicity:
        relationship["target_multiplicity"] = target_multiplicity
    return relationship


def _two_classes():
    return [{"name": "Usuario", "attributes": [], "operations": []}, {"name": "Rol", "attributes": [], "operations": []}]


@pytest.mark.django_db
class TestRelationshipQuality:
    """Associations, multiplicities and intermediate tables (user feedback after
    seeing `Usuarios 1 - 0..* Roles`, which should have been many-to-many)."""

    def test_a_proposal_must_state_both_multiplicities_but_the_image_import_schema_is_untouched(self):
        from apps.ai_assistant import tools

        def required(tool):
            return tool["parameters"]["properties"]["relationships"]["items"]["required"]

        assert {"source_multiplicity", "target_multiplicity"} <= set(required(tools.SUGGEST_UML_ADDITIONS))
        assert required(tools.EXTRACT_UML_DIAGRAM) == ["kind", "source_class_name", "target_class_name"]

    def test_the_model_is_taught_many_to_many_in_the_proposal_and_in_the_chat(self):
        from apps.ai_assistant import chat, tools

        guidance = tools.RELATIONSHIP_GUIDANCE
        assert "many-to-many" in guidance and "intermediate" in guidance and "0..*" in guidance
        assert guidance in proposals._PROPOSAL_INSTRUCTION
        assert guidance in chat._CHAT_INSTRUCTION

    def test_a_many_to_many_link_is_labelled_with_its_multiplicities_and_the_intermediate_table(self):
        organization, owner, *_ = make_org_with_roles()
        document = _document(organization, owner)

        proposal = _suggest(
            organization,
            document.id,
            owner,
            calls=[_suggestion(_two_classes(), [_link("Usuario", "Rol", "0..*", "0..*")])],
        )

        message = proposal.changes[-1]["message"]
        assert "0..* to 0..*" in message and "many-to-many" in message and "intermediate table" in message

    def test_a_one_to_many_link_shows_its_multiplicities_without_the_many_to_many_note(self):
        organization, owner, *_ = make_org_with_roles()
        document = _document(organization, owner)

        proposal = _suggest(
            organization,
            document.id,
            owner,
            calls=[_suggestion(_two_classes(), [_link("Rol", "Usuario", "1", "0..*")])],
        )

        message = proposal.changes[-1]["message"]
        assert "1 to 0..*" in message and "many-to-many" not in message

    def test_a_link_without_multiplicities_shows_the_defaults_the_diagram_would_really_get(self):
        organization, owner, *_ = make_org_with_roles()
        document = _document(organization, owner)

        proposal = _suggest(
            organization, document.id, owner, calls=[_suggestion(_two_classes(), [_link("Rol", "Usuario")])]
        )

        assert "0..1 to 0..*" in proposal.changes[-1]["message"]

    def test_approving_a_many_to_many_link_creates_a_relationship_with_both_ends_many(self):
        organization, owner, editor, *_ = make_org_with_roles()
        document = _document(organization, owner)
        proposal = _suggest(
            organization,
            document.id,
            owner,
            calls=[_suggestion(_two_classes(), [_link("Usuario", "Rol", "0..*", "1..*")])],
        )

        proposals.approve_proposal(
            organization=organization,
            doc_id=document.id,
            proposal_id=proposal.id,
            decided_by=editor,
            now=timezone.now(),
        )

        after = services.get_document(organization=organization, doc_id=document.id)
        (relationship,) = after.model.relationships
        assert (relationship.source.multiplicity.lower, relationship.source.multiplicity.upper) == (0, None)
        assert (relationship.target.multiplicity.lower, relationship.target.multiplicity.upper) == (1, None)

    def test_an_explicit_intermediate_class_keeps_its_own_attributes_and_both_links_in_order(self):
        organization, owner, *_ = make_org_with_roles()
        document = _document(organization, owner)
        classes = _two_classes() + [
            {"name": "UsuarioRol", "attributes": [{"name": "asignadoEn", "type": "Date"}], "operations": []}
        ]

        proposal = _suggest(
            organization,
            document.id,
            owner,
            calls=[
                _suggestion(
                    classes,
                    [
                        _link("Usuario", "UsuarioRol", "1", "0..*"),
                        _link("Rol", "UsuarioRol", "1", "0..*"),
                    ],
                )
            ],
        )

        assert [call["name"] for call in proposal.calls] == [
            "add_class",
            "add_class",
            "add_class",
            "add_attribute",
            "add_relationship",
            "add_relationship",
        ]
        assert all(change["ok"] for change in proposal.changes)


def _attribute_payload(class_id, name):
    from apps.uml_documents import schemas

    return schemas.AddAttributeIn.model_validate(
        {
            "type": "AddAttribute",
            "class_id": class_id,
            "attribute": {"id": f"attr-{name}", "name": name, "type": "String", "visibility": "private"},
        }
    )


def _three_changes(organization, owner, document):
    return _suggest(
        organization,
        document.id,
        owner,
        calls=[
            GeminiFunctionCall(name="add_class", args={"name": "Pedido"}),
            GeminiFunctionCall(name="add_class", args={"name": "Cliente"}),
            GeminiFunctionCall(
                name="add_attribute",
                args={"class_name": "Pedido", "attribute_name": "total", "attribute_type": "Decimal"},
            ),
        ],
    )


@pytest.mark.django_db
class TestPartialApproval:
    def _approve(self, organization, document, proposal, editor, selected):
        return proposals.approve_proposal(
            organization=organization,
            doc_id=document.id,
            proposal_id=proposal.id,
            decided_by=editor,
            now=timezone.now(),
            selected=selected,
        )

    def test_only_the_selected_changes_are_applied_and_recorded(self):
        organization, owner, editor, *_ = make_org_with_roles()
        document = _document(organization, owner)
        proposal = _three_changes(organization, owner, document)

        approved = self._approve(organization, document, proposal, editor, [1])

        assert approved.status == "approved"
        assert approved.applied_indices == [1]
        after = services.get_document(organization=organization, doc_id=document.id)
        assert [c.name for c in after.model.classes] == ["Cliente"]

    def test_a_class_and_its_attribute_can_be_applied_together_without_the_rest(self):
        organization, owner, editor, *_ = make_org_with_roles()
        document = _document(organization, owner)
        proposal = _three_changes(organization, owner, document)

        approved = self._approve(organization, document, proposal, editor, [2, 0])

        assert approved.applied_indices == [0, 2]
        after = services.get_document(organization=organization, doc_id=document.id)
        pedido = next(c for c in after.model.classes if c.name == "Pedido")
        assert [a.name for a in pedido.attributes] == ["total"]
        assert [c.name for c in after.model.classes] == ["Pedido"]

    def test_omitting_the_selection_still_applies_everything(self):
        organization, owner, editor, *_ = make_org_with_roles()
        document = _document(organization, owner)
        proposal = _three_changes(organization, owner, document)

        approved = self._approve(organization, document, proposal, editor, None)

        assert approved.applied_indices == [0, 1, 2]
        after = services.get_document(organization=organization, doc_id=document.id)
        assert sorted(c.name for c in after.model.classes) == ["Cliente", "Pedido"]

    def test_an_attribute_without_its_class_is_refused_and_nothing_changes(self):
        organization, owner, editor, *_ = make_org_with_roles()
        document = _document(organization, owner)
        proposal = _three_changes(organization, owner, document)

        with pytest.raises(proposals.InvalidSelectionError):
            self._approve(organization, document, proposal, editor, [2])

        after = services.get_document(organization=organization, doc_id=document.id)
        assert after.revision == document.revision
        assert proposals.get_proposal(
            organization=organization, doc_id=document.id, proposal_id=proposal.id
        ).status == "pending"

    @pytest.mark.parametrize("selected", [[], [9], [-1]])
    def test_an_empty_or_out_of_range_selection_is_refused(self, selected):
        organization, owner, editor, *_ = make_org_with_roles()
        document = _document(organization, owner)
        proposal = _three_changes(organization, owner, document)

        with pytest.raises(proposals.InvalidSelectionError):
            self._approve(organization, document, proposal, editor, selected)

    def test_a_change_that_cannot_be_applied_blocks_only_when_it_is_selected(self):
        organization, owner, editor, *_ = make_org_with_roles()
        document = _document(organization, owner)
        proposal = _suggest(
            organization,
            document.id,
            owner,
            calls=[
                GeminiFunctionCall(name="add_class", args={"name": "Pedido"}),
                GeminiFunctionCall(name="rename_class", args={"class_name": "Ghost", "new_name": "X"}),
            ],
        )

        with pytest.raises(proposals.UnapplicableProposalError):
            self._approve(organization, document, proposal, editor, [1])
        approved = self._approve(organization, document, proposal, editor, [0])

        assert approved.applied_indices == [0]


@pytest.mark.django_db
class TestListAndBroadcast:
    def test_lists_only_pending_proposals_and_marks_outdated_ones_stale(self):
        organization, owner, editor, *_ = make_org_with_roles()
        document = _document(organization, owner)
        old = _suggest(organization, document.id, owner)
        _add_class(organization, document.id, "Persona")
        fresh = _suggest(organization, document.id, owner)
        rejected = _suggest(organization, document.id, owner)
        proposals.reject_proposal(
            organization=organization, doc_id=document.id, proposal_id=rejected.id, decided_by=editor, now=timezone.now()
        )

        listed = proposals.list_proposals(organization=organization, doc_id=document.id)

        assert [item.id for item in listed] == [fresh.id]
        assert proposals.get_proposal(organization=organization, doc_id=document.id, proposal_id=old.id).status == "stale"

    def test_creating_and_deciding_broadcast_the_proposal_to_the_document_group(self):
        organization, owner, editor, *_ = make_org_with_roles()
        document = _document(organization, owner)

        with mock.patch("apps.ai_assistant.proposals.services.broadcast_event") as broadcast:
            with pytest.MonkeyPatch.context() as patch:
                patch.setattr("django.db.transaction.on_commit", lambda fn: fn())
                proposal = _suggest(organization, document.id, owner)
                proposals.reject_proposal(
                    organization=organization,
                    doc_id=document.id,
                    proposal_id=proposal.id,
                    decided_by=editor,
                    now=timezone.now(),
                )

        types = [call.kwargs["payload"]["type"] for call in broadcast.call_args_list]
        assert types == ["proposal.update", "proposal.update"]
        assert broadcast.call_args_list[-1].kwargs["payload"]["proposal"]["status"] == "rejected"
