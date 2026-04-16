## ADDED Requirements

### Requirement: Homepage can render supported icon metadata for official routes

The official public route catalog MUST allow Homepage entries to reference supported Homepage icon identifiers so official routes do not render broken image placeholders.

#### Scenario: Official route uses supported icon metadata

- **WHEN** an enabled official route declares supported Homepage icon metadata
- **THEN** the rendered Homepage configuration MUST reference that icon metadata
- **AND** the browser-visible Homepage card MUST not render a broken image placeholder for that route

### Requirement: Official route catalog can carry optional Homepage widget metadata

The official public route catalog MUST support optional Homepage widget metadata so richer service cards remain derived from the same catalog as the route itself.

#### Scenario: Official route declares widget metadata

- **WHEN** an enabled official route includes Homepage widget metadata
- **THEN** the rendered Homepage services configuration MUST include the matching widget block for that service
- **AND** routes without widget metadata MUST continue to render as plain links without requiring a second service list
