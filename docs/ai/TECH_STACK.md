# Tech Stack

This reflects the **corrected** stack per the real exam spec
(`product-04-next-django.md`), not the originally scaffolded generic
CRUD stack. Items marked "in progress" are being applied by a parallel
workstream at the time of writing; see `CURRENT_STATE.md` for what is
confirmed vs. pending.

## Backend (the CASE tool's own backend)

| Technology | Role | Status |
|---|---|---|
| Python 3.13+ | Language runtime | existing |
| Django 5.2 LTS | Web framework | existing |
| **Django Ninja** | API layer (replaces Django REST Framework) | in progress |
| Django ORM | Persistence | existing |
| **Django Channels + Daphne** | ASGI server, realtime/WebSocket | in progress |
| PostgreSQL | Relational database | existing |
| **Argon2** (via Django password hasher) | Password hashing | in progress |
| **PyJWT** | Token-based auth | in progress |
| Pydantic 2 | Schema validation (used by Django Ninja) | in progress |

Django REST Framework is being **removed**, not kept alongside Ninja.

## Frontend (the CASE tool's own frontend)

| Technology | Role | Status |
|---|---|---|
| Next.js (App Router) + TypeScript | Framework | existing |
| **Tailwind CSS** | Styling | in progress |
| **shadcn/ui** | Component library | in progress |
| **Cytoscape.js** | UML canvas rendering engine | in progress |
| **cytoscape-fcose** | Initial auto-layout for the canvas | in progress |
| **Jotai** | Client-side state management | in progress |
| Native WebSocket | Realtime client transport | planned (with Channels work) |

## Mobile (the CASE tool's own client — instructor requirement)

| Technology | Role | Status |
|---|---|---|
| **Flutter** | Real mobile client for the main CASE tool | bare scaffold only |

This is an explicit, non-negotiable instructor requirement, independent of
the document's own Android generation strategy below. It is a real client
app to be built out, not a placeholder to be dropped.

## Testing

| Technology | Scope | Status |
|---|---|---|
| **pytest + pytest-django + hypothesis** | Backend unit/integration/property tests | in progress (bootstrap) |
| **Vitest + React Testing Library** | Frontend unit/component tests | in progress (bootstrap) |
| **Cypress** | End-to-end tests | planned, not yet bootstrapped |

## Interoperability / generation tooling (used by the tool, not shipped in it)

| Technology | Role |
|---|---|
| UML 2.5.1 | Reference UML subset |
| XMI 2.1 | Import/export interchange format |
| Enterprise Architect | Target interoperability tool |
| defusedxml + lxml | Safe XML parsing/generation |
| Jinja2 + LibCST | Code generation templating/AST manipulation |
| OpenAPI (native to Django Ninja) | API spec generation for the tool's own API |

## Local AI / voice (run by the CASE tool, offline-capable)

| Technology | Role |
|---|---|
| ONNX Runtime + Hugging Face Optimum | Local inference runtime |
| Qwen3 1.7B (ONNX) | Text intent extraction for the assistant |
| Moondream (ONNX) | Image → UML recognition |
| Vosk (Spanish, local model) | Speech-to-text |
| OpenCV-Python | Image preprocessing |

None of this is implemented yet; it is a late-cycle target per spec
section 37.

## Generated-app stack (what the tool outputs for end users — distinct from the tool's own stack above)

| Layer | Technology |
|---|---|
| Backend | Java 21 LTS + Spring Boot 4.x + Spring Data JPA + Hibernate + PostgreSQL + Gradle + Jakarta Validation + Jackson + springdoc-openapi |
| Frontend | Next.js App Router + shadcn/ui |
| Android | Next.js PWA + Capacitor (wraps the same generated Next.js code) |

This stack is **fixed regardless of the tool's own stack** — the spec is
explicit that the tool's implementation choices must never leak into or
replace the generated backend's mandated Spring Boot stack.

## Methodology

**SDD (Spec-Driven Development)**, hybrid mode: OpenSpec files (`openspec/`)
+ Engram persistent memory. Adopted going forward for all feature work,
given the scope of the real spec and its own section-1 mandate for
use-case cycles, acceptance criteria, and a separate real-state document.
