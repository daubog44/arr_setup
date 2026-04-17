## ADDED Requirements

### Requirement: Auth-backed Homepage widgets must use live-compatible backend surfaces

When the official route catalog enables an auth-backed Homepage widget, the repo-managed widget configuration MUST match the backend protocol and authentication surface that the live service actually accepts.

#### Scenario: Grafana widget reaches a live-compatible API surface

- **GIVEN** the official route catalog enables the Grafana Homepage widget
- **WHEN** Homepage refreshes the Grafana widget
- **THEN** the widget MUST not fail with an HTTP proxy redirect/protocol error
- **AND** the Homepage card MUST not surface `HTTP status 500` or `API Error Information`
- **AND** the widget's authenticated API calls SHOULD stay on the in-cluster Grafana service instead of depending on the public edge path

#### Scenario: qBittorrent widget uses the reconciled API password

- **GIVEN** the official route catalog enables the qBittorrent Homepage widget
- **WHEN** the downloader stack reaches steady state
- **THEN** qBittorrent MUST accept the secret-backed password used by Homepage
- **AND** the Homepage card MUST not surface `API Error Information`

#### Scenario: Secret-backed widget credentials trigger rollout and startup convergence

- **GIVEN** Homepage or qBittorrent widget credentials change in the repo-managed secret inputs
- **WHEN** ArgoCD reconciles the updated manifests
- **THEN** the Homepage deployment and downloader stack MUST roll to pick up the new secret material
- **AND** qBittorrent MUST seed the desired WebUI password before steady state instead of depending on temporary-password log scraping alone

### Requirement: Browser verification fails on Homepage widget API errors

The repo-managed browser verification path MUST fail when the public Homepage route still renders broken widget states for official auth-backed widgets.

#### Scenario: Homepage surfaces widget API failures

- **WHEN** the public Homepage route renders `API Error Information` or `HTTP status 500`
- **THEN** the browser verification command MUST fail
- **AND** the failure message MUST identify Homepage widget surface drift instead of treating the page as healthy
