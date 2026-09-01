# Project Vision

> **Source of truth**: `product-04-next-django.md` (repo root) is the frozen,
> authoritative product specification. It must never be edited to reflect
> progress, decisions, or implementation status — that belongs in
> `CURRENT_STATE.md` and `DECISIONS_LOG.md`. This file is a working summary
> of that document and a pointer back to it, kept in the team's own words so
> it stays quick to re-read; whenever the two disagree, the root document
> wins.

## What this project actually is

This is **not** a generic CRUD scaffold. The real exam assignment (Variant 4,
`product-04-next-django.md`) is an **offline-first, collaborative CASE tool
for UML class diagramming** that also generates complete, runnable
applications from the diagrams it produces.

A user (or a small LAN-connected team) draws or dictates a UML class model.
That model — never the canvas, never any one input format — is the single
source of truth. From it, the tool can:

- render/edit the diagram interactively (manual editing, real-time
  multi-user collaboration with presence);
- accept the same model from an imported image, a spoken command, or an
  XMI 2.1 file (Enterprise Architect interoperability);
- validate it with one shared validation engine reused everywhere
  (save, import, collaboration, assistant, generation);
- transform it deterministically into a relational schema;
- generate a compilable Spring Boot backend, a Next.js frontend, an Android
  package (via Capacitor), OpenAPI + a Postman collection, and a "Domain
  Manifest" describing the generated app's capabilities;
- let end users of the *generated* app operate it through a natural-language
  or voice assistant, constrained to a small closed set of validated
  commands.

The whole system is designed to run **without Internet access** once local
AI models and dependencies are installed — local LLM inference (Qwen3 via
ONNX Runtime), local image-to-UML inference (Moondream), and local Spanish
speech-to-text (Vosk) are core requirements, not optional add-ons.

## Guiding principles (from the spec)

1. **One canonical model.** All inputs (manual edit, image, voice, XMI)
   converge into a single `CanonicalUmlModel`. All outputs (canvas, XMI,
   relational model, generated backend/frontend, OpenAPI, Domain Manifest)
   are derived from that same model. The canvas is a view, never the source
   of truth.
2. **One validation engine, reused everywhere** — not duplicated per
   feature.
3. **All mutation goes through one pipeline** (`UmlCommand` → Command Bus →
   Executor), which is also what makes Undo/Redo and realtime collaboration
   share the same contract.
4. **AI is constrained, never trusted blindly.** Output from the text
   assistant, the voice pipeline, or the image-to-UML pipeline is always
   validated before being applied — there is no direct AI-to-model write
   path, and the assistant in the *generated* app can only invoke a small,
   explicit allow-listed set of operations.
5. **The tool's own stack and the stack it generates are independent
   decisions.** The tool is built with Django/Next.js; everything it
   generates for end users is Java 21 + Spring Boot on the backend and
   Next.js + shadcn/ui on the frontend, regardless of what the tool itself
   is built with.
6. **Offline-first and LAN-first.** Nothing essential (editing,
   collaboration on a LAN, local AI/STT, running a generated app) should
   require Internet access.
7. **Incremental, use-case-driven delivery.** Per section 1 of the spec,
   the assignment explicitly requires deriving use cases from the document,
   grouping them into cycles, proposing acceptance criteria, implementing
   one use case at a time, and maintaining a real, separate state document
   (`CURRENT_STATE.md` in this repo) — never treating the spec document
   itself as a progress tracker.

## Two distinct mobile requirements — do not conflate

The spec's own generated-output strategy for Android (section 26) is
**Next.js PWA + Capacitor**, wrapping the same generated Next.js code — this
applies to the applications the tool generates for its end users, not to the
tool itself. Separately, the course instructor requires this project to
also ship a real **Flutter** mobile client (`mobile/`) for the CASE tool
itself. Both requirements are mandatory and coexist; neither replaces the
other. See `TECH_STACK.md` and `ARCHITECTURE.md` for how each is scoped.

## Methodology

Given the scope jump from "simple scaffold" to "full CASE tool platform",
the project has adopted **Spec-Driven Development (SDD)** — hybrid mode:
OpenSpec files (`openspec/`) plus Engram persistent memory — for all future
feature work. See `DECISIONS_LOG.md` for the rationale and `NEXT_STEPS.md`
for the first planned SDD cycle.

## What this file is not

This file does not restate all 40 sections of `product-04-next-django.md`
(UI/UX identity spec, exact command families, exact validation contracts,
exact generation rules, testing strategy, MVP checklist, recommended
implementation order, etc.). Read the root document directly for anything
beyond a vision-level summary — this file exists to be re-read quickly at
the start of a session, not to substitute for it.
