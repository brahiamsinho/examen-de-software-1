# Deterministic Architecture Audit

## Scope and contract

Issue #10 adds a read-only architectural-quality analysis of Modelia's
canonical UML class model. It is deliberately separate from
`apps.uml_modeling.validation`: validation reports formal UML diagnostics;

The pure entry point is `backend/apps/architecture_audit/analyzer.py:audit`.
It accepts only `CanonicalUmlModel` and has no Django, database, clock,
randomness, network or LLM dependency. `report(...)` produces contract `1.0`

`GET /api/orgs/{org_slug}/documents/{doc_id}/architecture-audit` loads an

```json
{
  "contract_version": "1.0",
  "rules_version": "1.0",
  "document": { "id": "uuid", "revision": 3 },
  "summary": { "ERROR": 0, "WARNING": 1, "INFO": 0 },
  "findings": [{
    "id": "ar-002-...",
    "rule_id": "AR-002",
    "rule_name": "Acoplamiento elevado",
    "rule_purpose": "Detecta clases conectadas con muchas relaciones directas.",
    "severity": "WARNING",
    "title": "...",
    "explanation": "...",
    "evidence": "...",
    "element_ids": ["real-class-id"],
    "recommendation": "..."
  }]
}
```

The endpoint allows every organization member, just like other document read
operations. Membership resolves before the tenant-scoped document lookup, so
cross-organization access remains a 404. It never invokes the command bus,
increments a revision, writes a record or broadcasts an event.

Exports are the same report: `GET .../architecture-audit/export?format=json`
report for equivalent JSON/Markdown downloads, avoiding a second request and
ensuring it exports what was inspected.

## Rule catalog

| Id | Severity | Exact activation | Evidence | Limitation |
| --- | --- | --- | --- | --- |
| AR-001 | INFO | A class has zero incident valid relationships. | Class id/name and count `0`. | Value objects or incomplete diagrams can intentionally be isolated. |
| AR-002 | WARNING | A class has at least 5 incident valid relationships. | Class id/name, count and threshold `5`. | Does not measure direction or semantic weight. |
| AR-003 | WARNING | A class has generalization depth at least 4. | Class id/name, computed depth and threshold `4`. | Only sees modeled inheritance; formal generalization cycles stay in UML validation. |
| AR-004 | WARNING | A class has at least 10 attributes plus operations. | Class id/name, each count, total and threshold `10`. | Does not inspect operation implementations. |
| AR-005 | WARNING | A strongly connected component has two or more classes, or a non-generalization self-loop. | Canonically sorted real class ids/names in the cycle. | Associations can be cyclic by intentional domain design. |

Only relationships whose endpoint class ids exist in the canonical model are
considered. This prevents a quality recommendation from inventing evidence
for a dangling relationship already covered by formal validation.

## Extension policy

Add a rule by introducing a stable `AR-xxx` id in `RULES`, documenting its
threshold/evidence/limitations here, adding pure fixtures for activation and
non-activation, and preserving canonical output order. Breaking a rule's
meaning requires a rules-version increase. Breaking report fields requires a
contract-version increase; additive fields are compatible with `1.x` clients.

## AI boundary

The web backend currently has only OpenAI/Gemini remote provider adapters;
the on-device mobile chat does not expose UML audit tools. No suitable local
web provider exists, so issue #10 intentionally does not add an AI
explanation action. Any future local explanation must consume an immutable
finding payload after the deterministic audit, return separate non-authoritative
text, and never alter report findings, ids, severities or exports.
