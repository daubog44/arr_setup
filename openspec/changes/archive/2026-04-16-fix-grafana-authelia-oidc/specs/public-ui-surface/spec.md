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
- **AND** `headlamp` MUST be `edge_forward_auth`
- **AND** `semaphore`, `grafana`, and `argocd` MUST be `native_oidc`
- **AND** `jellyfin`, `radarr`, `sonarr`, `prowlarr`, `autobrr`, and `qbittorrent` MUST be `app_native`

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
