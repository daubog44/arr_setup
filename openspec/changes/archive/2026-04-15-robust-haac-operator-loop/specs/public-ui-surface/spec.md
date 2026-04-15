# public-ui-surface Delta

## MODIFIED Requirements

### Requirement: Single public UI catalog

The system MUST derive official browser-facing routes from one declarative catalog.

#### Scenario: Published UI routes are rendered

- **WHEN** the GitOps manifests and Homepage configuration are rendered
- **THEN** the published HTTPRoutes, Homepage links, Homepage aliases, and endpoint verification list MUST come from the same declared route catalog
- **AND** the catalog MUST support route metadata for namespace, service, port, Homepage label, auth posture, route enablement, and optional alias entries
