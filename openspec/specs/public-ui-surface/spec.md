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

Published app UIs MUST declare an explicit per-route auth strategy in the public UI catalog, and the declared strategy MUST match the live browser-auth behavior.

#### Scenario: Official auth matrix is rendered

- **WHEN** the official public UI catalog is rendered
- **THEN** `authelia` MUST be `public`
- **AND** `homepage`, `ntfy`, `falco`, `longhorn`, and `headlamp` MUST be `edge_forward_auth`
- **AND** `semaphore`, `grafana`, and `argocd` MUST be `native_oidc`
- **AND** `jellyfin`, `radarr`, `sonarr`, `prowlarr`, `autobrr`, `qbittorrent`, and `litmus` MUST be `app_native`

### Requirement: Falco and Litmus are first-class official UIs when enabled

The operator-visible UI catalog MUST include Falco and Litmus when those UIs are intentionally published, and Litmus MUST remain a single canonical entry when enabled.

#### Scenario: Litmus stays visible as one canonical Homepage entry

- **WHEN** Litmus is enabled in the official route catalog
- **THEN** Homepage MUST include the primary `Litmus` link
- **AND** Homepage MUST NOT render a duplicate `ChaosTest` alias for the same route

#### Scenario: Litmus app-native login is repo-managed

- **WHEN** Litmus is published as an official `app_native` route
- **THEN** the chart MUST consume a repo-managed existing secret for `ADMIN_USERNAME` and `ADMIN_PASSWORD`
- **AND** the browser verification flow MUST prove that those repo-managed credentials reach the Litmus application after the initial login form
- **AND** the route MUST NOT remain behind the shared Authelia forward-auth middleware

### Requirement: Official UI verification matches the catalog

Endpoint verification MUST evaluate exactly the official published UI surface.

#### Scenario: Final public URL verification runs

- **WHEN** the operator runs endpoint verification or reaches the final `task up` URL summary
- **THEN** the verification list MUST include every enabled official UI route and no unsupported wildcard hosts
- **AND** each result MUST report the URL, service, namespace, and declared auth strategy

#### Scenario: Browser verification fallback is available when MCP is unavailable

- **WHEN** browser-level verification is required for the official public UI surface
- **THEN** the repo MUST prefer Playwright MCP when it is available in the client
- **AND** the repo MUST provide a repo-local Playwright CLI fallback when Playwright MCP is unavailable
- **AND** the verification contract MUST stay the same across both paths

