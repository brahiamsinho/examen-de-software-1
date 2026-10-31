# Image import completeness — 2026-10-31

## Problem

A real whiteboard diagram created three classes but omitted visible attributes
and relationships.

## Root cause

The OpenAI image path exposed independent command tools, allowing the model to
return only `add_class` calls without violating the tool contract.

## Correction

Image import now requires one structured `extract_uml_diagram` function. The
backend expands its classes, members and relationships into the existing
validated command pipeline.

A second real import showed that the vision model used handwritten UML's bare
`*` multiplicity shorthand. The existing command grammar correctly requires a
lower bound, so the image-only adapter now normalizes `*` and `n` to `0..*`,
and `1..n` to `1..*` before validation.

## Verification

- RED: structured extraction was unsupported and produced one failed command.
- GREEN: `docker compose exec -T backend pytest apps/ai_assistant` — 90 passed.

## Remaining proof

Repeat the real-photo import and verify attributes, relationships and
multiplicities visually.
