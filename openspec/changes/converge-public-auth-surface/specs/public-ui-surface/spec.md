## MODIFIED Requirements

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
- **AND** `homepage`, `ntfy`, `litmus`, `falco`, and `longhorn` MUST be `edge_forward_auth`
- **AND** `headlamp`, `semaphore`, `grafana`, and `argocd` MUST be `native_oidc`
- **AND** `jellyfin`, `radarr`, `sonarr`, `prowlarr`, `autobrr`, and `qbittorrent` MUST be `app_native`

#### Scenario: Browser verification runs for a native-OIDC route

- **WHEN** browser-level verification runs for a `native_oidc` route
- **THEN** verification MUST prove the OIDC flow completes to the application landing page after Authelia authentication
- **AND** a bare `302` redirect MUST NOT be considered sufficient proof of correctness
- **AND** the registered OIDC client MUST allow the token endpoint auth method used by the deployed application build

#### Scenario: Headlamp native OIDC is cluster-converged

- **WHEN** `headlamp` is declared as `native_oidc`
- **THEN** Headlamp MUST be configured with an OIDC client ID, client secret, issuer URL, and `/oidc-callback` redirect URI
- **AND** the K3s API server MUST be configured to trust the same OIDC issuer and client audience that Headlamp uses for browser login
- **AND** the browser verification flow MUST land on the Headlamp application instead of the internal login page or an invalid request page

#### Scenario: Browser verification runs for an app-native route

- **WHEN** browser-level verification runs for an `app_native` route
- **THEN** the application MUST present its own login UI or authenticated landing page
- **AND** the route MUST NOT be considered correct if it redirects through the shared Authelia forward-auth chain

#### Scenario: Control-plane native OIDC suppresses redundant local login UI

- **WHEN** repo-side config supports disabling the redundant local login UI for a `native_oidc` control-plane app
- **THEN** that local login UI MUST be disabled
- **AND** Semaphore verification MUST fail if `/api/auth/login` still reports `login_with_password=true`

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

### Requirement: Falco and Litmus are first-class official UIs when enabled

The operator-visible UI catalog MUST include Falco and Litmus when those UIs are intentionally published.

#### Scenario: Falco is enabled

- **WHEN** Falco is enabled in operator inputs
- **THEN** the official route catalog MUST publish the Falcosidekick Web UI through the shared ingress pattern
- **AND** Homepage MUST include the Falco UI link
- **AND** the Falco profile MUST avoid the known unprivileged-LXC runtime-probe crash and persistent-Redis failure modes of this cluster
- **AND** runtime sensor scheduling MUST remain explicit opt-in on compatible nodes instead of assuming every unprivileged LXC worker can host the probe
- **AND** the compatible-node opt-in MUST be expressible from repo-managed operator inputs rather than as an undocumented manual cluster label

#### Scenario: Litmus aliases stay visible on Homepage

- **WHEN** Litmus is enabled in the official route catalog
- **THEN** Homepage MUST include the primary `Litmus` link
- **AND** Homepage MUST also include the `ChaosTest` alias derived from the same route catalog entry

#### Scenario: Edge-auth UI uses shared auth

- **WHEN** Falco, Litmus, Homepage, Longhorn, or another official `edge_forward_auth` UI is published
- **THEN** that route MUST be protected through the shared Authelia forward-auth chain
