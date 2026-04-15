# public-ui-surface Specification

## Purpose
Define the stable public UI surface for the homelab so routing, Homepage, auth posture, and endpoint verification all derive from one catalog.
## Requirements
### Requirement: Single public UI catalog

The system MUST derive official browser-facing routes from one declarative catalog.

#### Scenario: Published UI routes are rendered

- **WHEN** the GitOps manifests and Homepage configuration are rendered
- **THEN** the published HTTPRoutes, Homepage links, and endpoint verification list MUST come from the same declared route catalog
- **AND** the catalog MUST support route metadata for namespace, service, port, Homepage label, auth posture, and route enablement

### Requirement: Disabled routes stay out of the official surface

Opt-in platform features MUST NOT create dead official URLs when disabled.

#### Scenario: Falco stays disabled

- **WHEN** Falco is disabled through operator inputs
- **THEN** the official route catalog MUST NOT render a Falco HTTPRoute
- **AND** Homepage MUST NOT render a Falco link
- **AND** endpoint verification MUST NOT report Falco as a required URL

### Requirement: Official app UIs are protected by Authelia

Published app UIs MUST be protected through the shared Authelia forward-auth path unless the route is explicitly marked public.

#### Scenario: Protected route is rendered

- **WHEN** an official UI route is not explicitly public
- **THEN** the rendered HTTPRoute MUST include the Authelia forward-auth middleware chain
- **AND** the operator-facing endpoint report MUST identify that route as protected rather than public

### Requirement: Falco and Litmus are first-class official UIs when enabled

The operator-visible UI catalog MUST include Falco and Litmus when those UIs are intentionally published.

#### Scenario: Falco is enabled

- **WHEN** Falco is enabled in operator inputs
- **THEN** the official route catalog MUST publish the Falcosidekick Web UI through the shared ingress pattern
- **AND** Homepage MUST include the Falco UI link

#### Scenario: Litmus is installed

- **WHEN** Litmus is part of the platform application set
- **THEN** the official route catalog MUST publish the Litmus frontend UI
- **AND** Homepage MUST include the Litmus UI link

### Requirement: Official UI verification matches the catalog

Endpoint verification MUST evaluate exactly the official published UI surface.

#### Scenario: Final public URL verification runs

- **WHEN** the operator runs endpoint verification or reaches the final `task up` URL summary
- **THEN** the verification list MUST include every enabled official UI route and no unsupported wildcard hosts
- **AND** each result MUST report the URL, service, namespace, and auth posture
