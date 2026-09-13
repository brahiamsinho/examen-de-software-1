# Web UML Canvas Specification

## Purpose

Let an org member open a UML document, view classes/relationships on a
Cytoscape canvas, and mutate it (add class, attribute, association) through
the command bus, with non-blocking validation feedback. Auth is inherited
from `(app)/layout.tsx`'s guard; not re-specified here.

## Requirements

### Requirement: Document Page Load

`app/(app)/documents/[docId]/page.tsx` MUST load the document at `docId`,
scoped to the organization in `activeOrgSlugAtom`. It MUST render a
not-found state, not a crash, on a backend 404 (including the cross-tenant
case, per `uml-document-persistence`'s `GET` 404 semantics).

#### Scenario: Successful load renders the document

- GIVEN an active organization and a document id belonging to it
- WHEN the document page loads
- THEN it displays the document's classes, attributes, and relationships

#### Scenario: Cross-tenant or missing document shows not-found

- GIVEN a document id that does not resolve under the active organization
- WHEN the page loads and the API returns 404
- THEN a not-found state renders instead of a crash or blank screen

### Requirement: Create-Document Entry Point

The dashboard MUST show a "New Diagram" entry point only when an active
organization exists. Submitting a name MUST call `POST /documents` and
navigate to the new document's page on success.

#### Scenario: Entry point hidden without an active organization

- GIVEN no active organization is selected
- WHEN the dashboard renders
- THEN no "New Diagram" entry point is shown

#### Scenario: Creating a document navigates to its page

- GIVEN an active organization exists
- WHEN the user submits a name through the entry point
- THEN `POST /documents` is called and the user is navigated to the new page

### Requirement: Diagram Rendering

The canvas MUST render each class as a node listing its attributes, each
relationship as an edge, and MUST apply `fcose` auto-layout on load.

#### Scenario: Classes and relationships render as nodes and edges

- GIVEN a document with two attributed classes and one relationship
- WHEN the canvas renders
- THEN both classes appear as nodes with attributes, linked by one edge

#### Scenario: Auto-layout runs on load

- GIVEN a document with no persisted positions
- WHEN the canvas mounts
- THEN `fcose` layout runs and every node has a computed position

### Requirement: Add Class Command

Submitting the add-class form MUST send an `AddClass` command, refetch the
document, and the canvas MUST reflect the new class node.

#### Scenario: New class appears after submission

- GIVEN an open document
- WHEN the user submits a class name through the add-class form
- THEN `AddClass` is submitted, the document refetched, and the class shown

### Requirement: Add Attribute Command

The add-attribute form MUST offer only the eight primitive types (`String`,
`Text`, `Integer`, `Long`, `Decimal`, `Boolean`, `Date`, `DateTime`) and MUST
NOT offer an enumeration-reference option. Submission MUST send an
`AddAttribute` command for the selected class, then refetch.

#### Scenario: Attribute is added to a class

- GIVEN a class exists on the canvas
- WHEN the user submits a primitive-typed attribute for that class
- THEN `AddAttribute` is submitted, refetched, and the class lists it

#### Scenario: Enumeration types are not offered

- GIVEN the add-attribute form is open
- WHEN the user views the type options
- THEN only the eight primitives are selectable; no enumeration option exists

### Requirement: Add Relationship Command

Adding a relationship MUST use click-click: clicking a source class node,
then a target class node, then confirming submits one `AddRelationship`
command of kind `association`, followed by a refetch.

#### Scenario: Click-click creates an association

- GIVEN two class nodes are visible on the canvas
- WHEN the user clicks source, then target, then confirms
- THEN an `association` `AddRelationship` is submitted and, after refetch,
  a new edge connects the two classes

### Requirement: Non-Blocking Validation Panel

The validation panel MUST render every violation from
`CommandResultOut.validation.violations` (severity, code, message, path) and
MUST NOT block further editing regardless of severity.

#### Scenario: Violations render without blocking edits

- GIVEN a command response with one or more violations
- WHEN the response is received
- THEN the panel lists each violation's fields, and all forms stay usable

### Requirement: Graceful Handling of Malformed Command Responses

If a command submission returns an unexpected shape (including a `422
invalid_command_payload` error), the UI MUST show an error state, not crash,
and MUST keep the previously loaded document on screen.

#### Scenario: Malformed response degrades gracefully

- GIVEN a response that does not match the `CommandResultOut` shape
- WHEN the UI processes it
- THEN an error message shows instead of a crash, and the loaded document
  stays visible and usable
