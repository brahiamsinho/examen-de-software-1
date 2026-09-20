# Delta for Web UML Canvas

## ADDED Requirements

### Requirement: Generation Profile Command Type

The frontend `UmlCommandIn` TypeScript union MUST include a `SetGenerationProfile` variant with shape `{ type: "SetGenerationProfile"; element_id: string; profile: Record<string, unknown> | null }`, and that variant MUST be accepted by the existing `submitCommand` REST flow without introducing backend, persistence, canvas rendering, `defaultSort`, or Flutter/mobile behavior changes.

#### Scenario: Frontend command union accepts generation profile updates

- GIVEN frontend code builds a UML command for element `element-1` with profile `{ readOnly: true }`
- WHEN the command is typed as `UmlCommandIn`
- THEN the command MAY have `type: "SetGenerationProfile"`, `element_id: "element-1"`, and `profile: { readOnly: true }`
- AND the command is eligible to be sent through the existing `submitCommand` REST path

#### Scenario: Frontend command union accepts profile clear

- GIVEN frontend code builds a UML command for element `element-1` with no declared generation profile controls
- WHEN the command is typed as `UmlCommandIn`
- THEN the command MAY have `type: "SetGenerationProfile"`, `element_id: "element-1"`, and `profile: null`
- AND no backend or persistence contract is changed by this frontend type addition

### Requirement: Generation Profile Sidebar Card

The UML document page sidebar MUST render a Card titled `Perfil de generación` that lets the editor select class and attribute elements from the currently loaded CanonicalUmlModel and edit only these tri-state generation profile controls: class targets expose `auditable`, `readOnly`, and `crud`; attribute targets expose `searchable`, `sortable`, and `readOnly`. Each control MUST support `unset`, explicit `true`, and explicit `false`, where `unset` means undeclared and MUST be distinct from `false`.

#### Scenario: Sidebar shows the generation profile card

- GIVEN a UML document page has loaded a CanonicalUmlModel
- WHEN the sidebar renders
- THEN it shows a Card titled `Perfil de generación`
- AND the Card offers generation profile editing without changing canvas rendering

#### Scenario: Class selection shows class-level controls

- GIVEN the loaded CanonicalUmlModel contains class `Order`
- WHEN the user selects `Order` in the `Perfil de generación` Card
- THEN the Card shows tri-state controls for `auditable`, `readOnly`, and `crud`
- AND it does not show attribute-only controls `searchable` or `sortable`

#### Scenario: Attribute selection shows attribute-level controls

- GIVEN the loaded CanonicalUmlModel contains class `Order` with attribute `total`
- WHEN the user selects attribute `total` in the `Perfil de generación` Card
- THEN the Card shows tri-state controls for `searchable`, `sortable`, and `readOnly`
- AND it does not show class-only controls `auditable` or `crud`

#### Scenario: No selection shows an empty disabled state

- GIVEN no class or attribute is selected in the `Perfil de generación` Card
- WHEN the Card renders its controls area
- THEN it shows an empty or disabled no-selection state
- AND no profile command can be submitted from that state

### Requirement: Generation Profile Prefill

The generation profile Card MUST prefill its tri-state controls from `document.model.generation_metadata[elementId].profile` when that value is an object. Selection changes MUST recompute the prefilled controls for the newly selected class or attribute. Missing, malformed, or non-object profile metadata MUST be treated as all controls unset and MUST NOT crash the page.

#### Scenario: Existing class profile pre-fills class controls

- GIVEN class `Order` has `generation_metadata[Order.id].profile` equal to `{ auditable: true, readOnly: false, crud: ["create", "read", "update", "delete"] }`
- WHEN the user selects `Order` in the `Perfil de generación` Card
- THEN `auditable` is prefilled as explicit `true`
- AND `readOnly` is prefilled as explicit `false`
- AND `crud` is prefilled as explicit `true`

#### Scenario: Existing attribute profile pre-fills attribute controls

- GIVEN attribute `total` has `generation_metadata[total.id].profile` equal to `{ searchable: true, sortable: false, readOnly: true }`
- WHEN the user selects `total` in the `Perfil de generación` Card
- THEN `searchable` is prefilled as explicit `true`
- AND `sortable` is prefilled as explicit `false`
- AND `readOnly` is prefilled as explicit `true`

#### Scenario: Selection changes replace the prefilled values

- GIVEN class `Order` has `auditable` declared as `true`
- AND attribute `total` has `searchable` declared as `false`
- WHEN the user first selects `Order` and then selects `total`
- THEN the Card replaces the class-level controls with attribute-level controls
- AND the visible controls are prefilled from `total` rather than from `Order`

#### Scenario: Malformed metadata pre-fills as unset

- GIVEN the selected element has `generation_metadata[elementId].profile` that is missing, `null`, an array, or another non-object value
- WHEN the `Perfil de generación` Card derives its initial controls
- THEN all visible tri-state controls are unset
- AND the page does not crash

### Requirement: Generation Profile Submission

When a selected element's profile controls are submitted, the Card MUST send exactly one `SetGenerationProfile` command through the existing `submitCommand` REST flow and MUST update local UI state to the submitted values after success. The submitted profile MUST include only declared controls. If every visible control is unset, the Card MUST submit `profile: null`. For class targets, `crud` MUST map from tri-state UI to the existing profile vocabulary: unset omits `crud`, explicit `true` sends `crud: ["create", "read", "update", "delete"]`, and explicit `false` sends `crud: []`.

#### Scenario: Declared class controls submit a SetGenerationProfile command

- GIVEN class `Order` is selected in the `Perfil de generación` Card
- AND `auditable` is explicit `true`, `readOnly` is unset, and `crud` is explicit `false`
- WHEN the user submits the profile
- THEN the frontend sends one command through `submitCommand` with `type: "SetGenerationProfile"`
- AND the command has `element_id` equal to `Order.id`
- AND the command has `profile` equal to `{ auditable: true, crud: [] }`
- AND the Card updates its local controls to reflect the submitted values after the REST submission succeeds

#### Scenario: Declared attribute controls submit a SetGenerationProfile command

- GIVEN attribute `total` is selected in the `Perfil de generación` Card
- AND `searchable` is explicit `true`, `sortable` is unset, and `readOnly` is explicit `false`
- WHEN the user submits the profile
- THEN the frontend sends one command through `submitCommand` with `type: "SetGenerationProfile"`
- AND the command has `element_id` equal to `total.id`
- AND the command has `profile` equal to `{ searchable: true, readOnly: false }`

#### Scenario: All unset controls clear the profile

- GIVEN an element is selected in the `Perfil de generación` Card
- AND every visible tri-state control is unset
- WHEN the user submits the profile
- THEN the frontend sends one command through `submitCommand` with `type: "SetGenerationProfile"`
- AND the command has `element_id` equal to the selected element id
- AND the command has `profile: null`

#### Scenario: CRUD true maps to all operations

- GIVEN a class is selected in the `Perfil de generación` Card
- AND only `crud` is explicit `true`
- WHEN the user submits the profile
- THEN the submitted profile is `{ crud: ["create", "read", "update", "delete"] }`
- AND the submitted profile does not contain a raw boolean `crud` value

### Requirement: Generation Profile Scope Boundaries

This change MUST remain a frontend authoring surface only. It MUST NOT add or modify backend behavior, persistence behavior, canvas rendering, WebSocket behavior, `defaultSort` authoring, generated code behavior, or Flutter/mobile behavior.

#### Scenario: Excluded capabilities remain unchanged

- GIVEN the generation profile Card has been added to the UML document page
- WHEN the change is reviewed
- THEN no backend code, persistence contract, canvas rendering behavior, `defaultSort` authoring, generated Spring/Next/Domain Manifest behavior, WebSocket protocol, or Flutter/mobile behavior is introduced or changed by this delta
