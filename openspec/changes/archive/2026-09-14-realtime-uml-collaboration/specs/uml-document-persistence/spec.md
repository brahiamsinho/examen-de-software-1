# Delta for UML Document Persistence

## MODIFIED Requirements

### Requirement: Command Submission

`POST /orgs/{org_slug}/documents/{doc_id}/commands` MUST accept one
`{type, payload}` body mapped to a `UmlCommand` subtype via a
discriminated-union schema, apply it through `dispatcher.apply()`, persist
the resulting document, and return the new `revision` plus validation
diagnostics. It MUST require role `EDITOR` or higher. Command application
for a given document MUST be serialized: the server MUST hold a row lock on
the target `UmlDocument` for the duration of the read-apply-persist
sequence, so that two commands submitted concurrently against the same
document can never both read the same starting revision and race to save.
Each command MUST still apply incrementally against the latest persisted
revision at the time it acquires the lock.

(Previously: command application read the `UmlDocument` row without any
lock, so two concurrent submissions against the same document could both
read the same starting revision and one persisted result could silently
overwrite the other — a lost update.)

#### Scenario: Sequential commands persist across calls

- GIVEN an empty document owned by an `EDITOR`
- WHEN `AddClass` is submitted, then `AddAttribute` targeting the class just added is submitted in a second call
- THEN the second call's resulting document contains the class with the new attribute
- AND each call's returned `revision` increments by exactly 1 over the prior persisted revision

#### Scenario: Viewer is denied command submission

- GIVEN an authenticated user with role `VIEWER` on the document's organization
- WHEN they submit any command to `.../documents/{doc_id}/commands`
- THEN the request is rejected and the document is not modified

#### Scenario: Invalid result still persists with diagnostics

- GIVEN a document containing only class A
- WHEN `AddRelationship` is submitted with source A and a nonexistent target class id
- THEN the response is successful (not an error) and reflects the new revision containing the relationship
- AND the response's diagnostics are non-empty and include an `INVALID_RELATIONSHIP_ENDPOINT` entry
- AND the persisted document matches the returned state

#### Scenario: Concurrent commands against the same document do not lose an update

- GIVEN an existing document at revision N
- WHEN two `AddClass` commands are submitted concurrently against that
  document, both starting before either has persisted
- THEN both commands persist successfully, one serialized after the other
- AND the document's final revision is exactly N + 2
- AND both classes are present in the final persisted document
