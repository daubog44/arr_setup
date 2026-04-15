# public-ui-surface Specification

## MODIFIED Requirements

### Requirement: Official app UIs are protected by the declared auth strategy

Published app UIs MUST be protected according to an explicit per-route auth strategy declared in the public ingress catalog.

#### Scenario: Protected route is rendered

- **WHEN** an official UI route is rendered from the ingress catalog
- **THEN** the route MUST declare one of `public`, `edge_forward_auth`, `native_oidc`, or `app_native`
- **AND** `edge_forward_auth` routes MUST include the shared Authelia forward-auth middleware chain
- **AND** `native_oidc` routes MUST NOT include the shared Authelia forward-auth middleware chain
- **AND** `app_native` routes MUST NOT include the shared Authelia forward-auth middleware chain
- **AND** the operator-facing endpoint report MUST identify the declared auth strategy rather than only `public` or `protected`

#### Scenario: Browser verification runs for a native-OIDC route

- **WHEN** browser-level verification runs for a `native_oidc` route
- **THEN** verification MUST prove the OIDC flow completes to the application landing page after Authelia authentication
- **AND** a bare `302` redirect MUST NOT be considered sufficient proof of correctness

#### Scenario: Browser verification runs for an app-native route

- **WHEN** browser-level verification runs for an `app_native` route
- **THEN** the application MUST present its own login UI or authenticated landing page
- **AND** the route MUST NOT be considered correct if it redirects through the shared Authelia forward-auth chain

### Requirement: Official UI verification matches the catalog

Endpoint verification MUST evaluate exactly the official published UI surface and must honor each route's declared auth strategy.

#### Scenario: Final public URL verification runs

- **WHEN** the operator runs endpoint verification or reaches the final `task up` URL summary
- **THEN** the verification list MUST include every enabled official UI route and no unsupported wildcard hosts
- **AND** each result MUST report the URL, service, namespace, and declared auth strategy
- **AND** `edge_forward_auth` routes MUST only pass when the expected Authelia redirect or challenge is observed
- **AND** `public` routes MUST only pass when they answer directly
