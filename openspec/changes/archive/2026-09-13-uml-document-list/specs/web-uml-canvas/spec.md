# Delta for Web UML Canvas

## ADDED Requirements

### Requirement: Dashboard Document List

`/dashboard` MUST fetch and render the active organization's documents via
`useDocuments(orgSlug)`, with each row navigable to `/documents/{id}`. When
the active organization has zero documents, the dashboard MUST render an
empty state instead of a blank region.

#### Scenario: Documents render as navigable rows

- GIVEN the active organization has two documents
- WHEN the dashboard renders
- THEN both documents appear as rows, and clicking a row navigates to that
  document's `/documents/{id}`

#### Scenario: Zero documents renders an empty state

- GIVEN the active organization has zero documents
- WHEN the dashboard renders
- THEN an empty-state message renders instead of a blank list region

#### Scenario: Switching organizations shows that organization's documents

- GIVEN the active organization changes from organization `A` to
  organization `B`
- WHEN the dashboard re-renders
- THEN it fetches and displays organization `B`'s documents, not
  organization `A`'s

## MODIFIED Requirements

### Requirement: Create-Document Entry Point

The dashboard MUST show a "New Diagram" entry point inside a header row
that also contains a "Mis Diagramas" heading, positioned above the document
list, and only when an active organization exists. Submitting a name MUST
call `POST /documents` and navigate to the new document's page on success.
(Previously: the entry point rendered standalone, with no header row, no
heading, and no document list to sit above.)

#### Scenario: Entry point hidden without an active organization

- GIVEN no active organization is selected
- WHEN the dashboard renders
- THEN no "New Diagram" entry point is shown

#### Scenario: Creating a document navigates to its page

- GIVEN an active organization exists
- WHEN the user submits a name through the entry point
- THEN `POST /documents` is called and the user is navigated to the new page

#### Scenario: Entry point renders in the header, above the list

- GIVEN an active organization exists
- WHEN the dashboard renders
- THEN the "New Diagram" entry point appears in the same header row as the
  "Mis Diagramas" heading, positioned above the document list
