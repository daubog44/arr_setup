## MODIFIED Requirements

### Requirement: Falco and policy reporting are first-class official UIs when enabled

The operator-visible UI catalog MUST include security control-plane UIs when those surfaces are intentionally published.

#### Scenario: Policy reporting UI is enabled

- **WHEN** the policy reporting UI is intentionally enabled in the official route catalog
- **THEN** Homepage MUST include the policy reporting link
- **AND** endpoint verification MUST treat it as part of the official surface with an explicit auth strategy
