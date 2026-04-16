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

#### Scenario: Protected route is rendered

- **WHEN** an official UI route is rendered from the ingress catalog
- **THEN** it MUST declare one of `public`, `edge_forward_auth`, `native_oidc`, or `app_native`
- **AND** `edge_forward_auth` routes MUST include the shared Authelia forward-auth middleware chain
- **AND** `native_oidc` routes MUST NOT include the shared Authelia forward-auth middleware chain
- **AND** `app_native` routes MUST NOT include the shared Authelia forward-auth middleware chain
- **AND** the declared strategy MUST come from `auth_strategy`, not from the legacy `auth_enabled` boolean
- **AND** the operator-facing endpoint report MUST identify the declared auth strategy rather than only `public` or `protected`

#### Scenario: Official auth matrix is rendered

- **WHEN** the official public UI catalog is rendered
- **THEN** `authelia` MUST be `public`
- **AND** `homepage`, `ntfy`, `falco`, `longhorn`, and `headlamp` MUST be `edge_forward_auth`
- **AND** `semaphore`, `grafana`, and `argocd` MUST be `native_oidc`
- **AND** `jellyfin`, `radarr`, `sonarr`, `prowlarr`, `autobrr`, `qbittorrent`, and `litmus` MUST be `app_native`

#### Scenario: Browser verification runs for a native-OIDC route

- **WHEN** browser-level verification runs for a `native_oidc` route
- **THEN** verification MUST prove the OIDC flow completes to the application landing page after Authelia authentication
- **AND** a bare `302` redirect MUST NOT be considered sufficient proof of correctness
- **AND** the registered OIDC client MUST allow the token endpoint auth method used by the deployed application build
- **AND** any repo-managed secret that supplies the OIDC client secret to the application MUST expose that secret under the exact environment-variable or configuration key name consumed by the deployed application
- **AND** verification MUST fail if the browser remains on the application's login route with an OAuth or token-exchange error rendered in the page

#### Scenario: Headlamp uses a single-login fallback when native OIDC is not converged

- **WHEN** Headlamp native OIDC does not converge to the authenticated application in this repo
- **THEN** `headlamp` MUST NOT remain declared as `native_oidc`
- **AND** the route MUST fall back to `edge_forward_auth`
- **AND** the deployment MUST provide a repo-managed in-cluster kubeconfig so the browser lands on the Headlamp application without a second token prompt
- **AND** stale Headlamp OIDC client and secret artifacts MUST be removed from the repo-managed IdP configuration
- **AND** the mounted Kubernetes access level MUST be repo-managed and default to a non-admin read-only role

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

#### Scenario: Litmus stays visible as one canonical Homepage entry

- **WHEN** Litmus is enabled in the official route catalog
- **THEN** Homepage MUST include the primary `Litmus` link
- **AND** Homepage MUST NOT render a duplicate `ChaosTest` alias for the same route

#### Scenario: Litmus app-native login is repo-managed

- **WHEN** Litmus is published as an official `app_native` route
- **THEN** the chart MUST consume a repo-managed existing secret for `ADMIN_USERNAME` and `ADMIN_PASSWORD`
- **AND** the browser verification flow MUST prove that those repo-managed credentials reach the Litmus application after the initial login form
- **AND** the route MUST NOT remain behind the shared Authelia forward-auth middleware

#### Scenario: Edge-auth UI uses shared auth

- **WHEN** Falco, Litmus, Homepage, Longhorn, or another official `edge_forward_auth` UI is published
- **THEN** that route MUST be protected through the shared Authelia forward-auth chain

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
