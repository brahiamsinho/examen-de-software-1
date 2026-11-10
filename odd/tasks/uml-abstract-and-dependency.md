# UML 2.5: abstract classes and dependency
Branch: feat/uml-abstract-and-dependency (from docs/uml-2-5-conformance). Strategy: ask-on-risk. Runner: pytest in docker (backend), vitest (web), flutter test (mobile).

## Specs
- S1: "Si, implemeta el uml 2.5" (user chose slices 1 and 2 of docs/ai/UML_2_5_CONFORMANCE.md: abstract classes and dependency; slices 3-5 stay documented as future work).
- S2: A class can be marked abstract (`UmlClass.is_abstract`, default False). It is saved, shown in italics with `{abstract}` on the web canvas and the phone preview, exported to XMI (`isAbstract`) and read back. Existing diagrams keep opening (the field is optional).
- S3: A new relationship kind `dependency` (UML Dependency): a dashed line with an open arrow from the client to the supplier. It has no multiplicity. It does not take part in generation or relational mapping.
- S4: The generated Java is NOT changed: the generator works from relational tables, so abstraction and dependency are modeling-only. Documented as a limit.
- S5: `docs/ai/UML_2_5_CONFORMANCE.md` is updated to the new state.

## Tasks
- [x] T1 (S2): abstract classes in the backend: domain, codec, command, schemas, services, session log, XMI. Route: inline. Evidence: 18 new tests + backend suites for the touched apps (456 passed).
- [x] T2 (S2): abstract classes in web and mobile preview. Evidence: vitest 564 passed, flutter test 214 passed, analyze clean.
- [x] T3 (S3): dependency in the backend (domain, validation, mapping ignores it, XMI both ways). Evidence: 18 new tests.
- [x] T4 (S3): dependency in web and mobile preview. Evidence: vitest 569 passed, flutter test 216 passed, analyze clean.
- T5 (S5): conformance document and final suites.

## Log
- L1 (2026-11-10, user): "Si, implemeta el uml 2.5"
