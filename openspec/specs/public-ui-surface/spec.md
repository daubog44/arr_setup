# public-ui-surface Specification

## Purpose
Define the stable public UI surface for the homelab so routing, Homepage, auth posture, and endpoint verification all derive from one catalog.
## Requirements
### Requirement: Single public UI catalog

The system MUST derive official browser-facing routes from one declarative catalog.

#### Scenario: Published UI routes are rendered

- **WHEN** the GitOps manifests and Homepage configuration are rendered
- **THEN** the published HTTPRoutes, Homepage links, Homepage aliases, and endpoint verification list MUST come from the same declared route catalog
- **AND** the catalog MUST support route metadata for namespace, service, port, Homepage label, auth posture, route enablement, and optional alias entries

### Requirement: Disabled routes stay out of the official surface

Opt-in platform features MUST NOT create dead official URLs when disabled.

#### Scenario: Falco stays disabled

- **WHEN** Falco is disabled through operator inputs
- **THEN** the official route catalog MUST NOT render a Falco HTTPRoute
- **AND** Homepage MUST NOT render a Falco link
- **AND** endpoint verification MUST NOT report Falco as a required URL

### Requirement: Official app UIs use an explicit auth strategy

Published app UIs MUST declare an explicit per-route auth strategy in the public UI catalog.

#### Scenario: Protected route is rendered

- **WHEN** an official UI route is rendered from the ingress catalog
- **THEN** it MUST declare one of `public`, `edge_forward_auth`, `native_oidc`, or `app_native`
- **AND** `edge_forward_auth` routes MUST include the shared Authelia forward-auth middleware chain
- **AND** `native_oidc` routes MUST NOT include the shared Authelia forward-auth middleware chain
- **AND** `app_native` routes MUST NOT include the shared Authelia forward-auth middleware chain
- **AND** the declared strategy MUST come from `auth_strategy`, not from the legacy `auth_enabled` boolean
- **AND** the operator-facing endpoint report MUST identify the declared auth strategy rather than only `public` or `protected`

#### Scenario: Browser verification runs for a native-OIDC route

- **WHEN** browser-level verification runs for a `native_oidc` route
- **THEN** verification MUST prove the OIDC flow completes to the application landing page after Authelia authentication
- **AND** a bare `302` redirect MUST NOT be considered sufficient proof of correctness
- **AND** the registered OIDC client MUST allow the token endpoint auth method used by the deployed application build

#### Scenario: In-cluster native OIDC is not treated as supported without a converged browser flow

- **WHEN** an in-cluster control-plane UI advertises native OIDC but the browser flow still lands on the local login screen or unauthorized cluster state after the upstream identity step
- **THEN** the route MUST NOT remain declared as `native_oidc`
- **AND** the route MUST fall back to `edge_forward_auth` or another strategy that produces a single working login gate

#### Scenario: Browser verification runs for an app-native route

- **WHEN** browser-level verification runs for an `app_native` route
- **THEN** the application MUST present its own login UI or authenticated landing page
- **AND** the route MUST NOT be considered correct if it redirects through the shared Authelia forward-auth chain

#### Scenario: Control-plane native OIDC suppresses redundant local login UI

- **WHEN** repo-side config supports disabling the redundant local login UI for a `native_oidc` control-plane app
- **THEN** that local login UI MUST be disabled
- **AND** Semaphore verification MUST fail if `/api/auth/login` still reports `login_with_password=true`

### Requirement: Falco and Litmus are first-class official UIs when enabled

The operator-visible UI catalog MUST include Falco and Litmus when those UIs are intentionally published.

#### Scenario: Falco is enabled

- **WHEN** Falco is enabled in operator inputs
- **THEN** the official route catalog MUST publish the Falcosidekick Web UI through the shared ingress pattern
- **AND** Homepage MUST include the Falco UI link
- **AND** the Falco profile MUST avoid the known unprivileged-LXC runtime-probe crash and persistent-Redis failure modes of this cluster
- **AND** runtime sensor scheduling MUST remain explicit opt-in on compatible nodes instead of assuming every unprivileged LXC worker can host the probe
- **AND** the compatible-node opt-in MUST be expressible from repo-managed operator inputs rather than as an undocumented manual cluster label

#### Scenario: Edge-auth UI uses shared auth

- **WHEN** Falco, Litmus, Homepage, Longhorn, or another official `edge_forward_auth` UI is published
- **THEN** that route MUST be protected through the shared Authelia forward-auth chain

### Requirement: Official UI verification matches the catalog

Endpoint verification MUST evaluate exactly the official published UI surface.

#### Scenario: Final public URL verification runs

- **WHEN** the operator runs endpoint verification or reaches the final `task up` URL summary
- **THEN** the verification list MUST include every enabled official UI route and no unsupported wildcard hosts
- **AND** each result MUST report the URL, service, namespace, and declared auth strategy
