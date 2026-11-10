# Migrate Modelia's own database from PostgreSQL to MongoDB

Objective: Modelia's Django backend stores its data in MongoDB. The Spring code it GENERATES for users is untouched (it keeps its own database).
Branch: feature/mongodb-migration. Delivery: ask-on-risk. Test runner: `docker compose run --rm backend pytest`.

## Specs
- S1: "migrar la base de datos a nosql osea mongodb, solo del proyecto, el backend que se genere se mantendra asi" - only Modelia's persistence moves; `apps/spring_generator` output stays byte-identical.
- S2: "no hay datos que quiera conservar" - no data migration; start from an empty MongoDB, demo data is recreated by the existing seed.
- S3: Docker Compose (dev and prod) run a `mongo` service instead of `db`; settings read it from environment variables, never hardcoded.
- S4: Tenant isolation, roles (OWNER/EDITOR/VIEWER, other org = 404) and every API behave as before; the backend test suite (1692 tests) is green on MongoDB.
- S5: Assumption: the chosen driver is `django-mongodb-backend` (official), which forces Django 5.2 and `ObjectIdAutoField` defaults.

## Tasks
- T1 (S3,S5) spike: Django 5.2 + django-mongodb-backend + replica-set Mongo in compose; UUID pk, FK, unique and transactions proven by the full suite; select_for_update is a no-op. route: inline. status: done, commit d40ed06
- T2 (S4) models: M2M, Lower constraint, BigAutoField ids replaced; web and Flutter ids are strings. route: inline. status: done, commits d40ed06, 420b244, 33f8c5c
- T3 (S4) concurrency: config/transactions.py; owner-rule and proposal-decision thread tests; mutation-checked. route: inline. status: done, commit d40ed06
- T4 (S3) compose, env, docs (no CI exists). route: inline. status: done, commits d40ed06, b7651a2
- T5 (S1,S4) full suite (backend 1700, web 554, Flutter 201), real stack run, generator logic files unchanged, docs/ai. route: inline. status: done except the independent verification and an EC2 rehearsal

## Log
- L1 (user): "mira, surgieron unos problemas, primero que nada tenemos que migrar la base de datos a nosql osea mongodb, solo del proyecto, el backend  que se genere se mantendra asi, nose nada de nosql"
- L2 (user): "no hay datos que quiera conservar ya que es un proyecto apra rpesentar a un docente"
- L3 (finding): django-mongodb-backend 5.2.x needs Django 5.2 (repo pins 5.0). It has no select_for_update, no ManyToManyField, savepoints are no-ops, transactions need a replica set. Code uses select_for_update in organizations, uml_documents, ai_assistant, backend_deployments; ManyToMany in organizations.Organization.members; Lower() unique constraint on User.email; BigAutoField ids on ChatMessage and LogEntry that the web and the phone consume as integers.
- L4 (decision): the user said they did not follow the id question (A: string ObjectIds, B: integer counter); the assistant chose A.
- L5 (finding, fixed): the first real login with 'Owner@Demo.com' answered 401 because emails are now stored lowercased; the login now lowercases too (test first, commit 33f8c5c).
- Risk: items 3 (ids in the API change from integers to strings), 4 (concurrency: locks replaced by retried transactions), 5 (dependencies, compose, environment). Independent verification: done, see L6.
- L6 (verification): an independent verifier ran thread probes on the real MongoDB (last-owner, quota, confirm, proposals, versions, commands) and all guards held. One blocker, fixed: MongoDB's email__iexact is an unescaped regex, so the dot in john.smith@example.com matched johnxsmith@example.com (false duplicate, wrong member added, password reset sent to the wrong account). Lookups now use an exact match on the lowercased address; regression tests in apps/users/tests/test_services_email_lookup.py failed first. Stale db/Postgres comments and build envs were cleaned. Backend now 1713 passed. Not tested: more than 8 racing writers against one row (the retry budget is about 3 seconds).
