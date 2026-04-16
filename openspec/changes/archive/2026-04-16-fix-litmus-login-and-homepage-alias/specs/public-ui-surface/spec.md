## MODIFIED Requirements

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
