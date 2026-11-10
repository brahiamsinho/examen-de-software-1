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
- T1 (S3,S5) spike: Django 5.2 + django-mongodb-backend + replica-set Mongo in compose; prove UUID pk, FK, unique, transactions, select_for_update behavior. route: inline. status: pending
- T2 (S4) models: replace unsupported features (M2M, Lower constraint, BigAutoField ids, select_for_update). route: inline. status: pending
- T3 (S4) concurrency: re-express row locking as transactions / optimistic revision checks. route: inline. status: pending
- T4 (S3) compose, env, CI, docs. route: inline. status: pending
- T5 (S1,S4) full suite + differential check of generator output + docs/ai. route: inline. status: pending

## Log
- L1 (user): "mira, surgieron unos problemas, primero que nada tenemos que migrar la base de datos a nosql osea mongodb, solo del proyecto, el backend  que se genere se mantendra asi, nose nada de nosql"
- L2 (user): "no hay datos que quiera conservar ya que es un proyecto apra rpesentar a un docente"
- L3 (finding): django-mongodb-backend 5.2.x needs Django 5.2 (repo pins 5.0). It has no select_for_update, no ManyToManyField, savepoints are no-ops, transactions need a replica set. Code uses select_for_update in organizations, uml_documents, ai_assistant, backend_deployments; ManyToMany in organizations.Organization.members; Lower() unique constraint on User.email; BigAutoField ids on ChatMessage and LogEntry that the web and the phone consume as integers.
