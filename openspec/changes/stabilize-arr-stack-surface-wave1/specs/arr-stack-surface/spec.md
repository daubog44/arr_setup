## ADDED Requirements

### Requirement: The repo-managed arr stack includes a request-management surface

The repo-managed media stack MUST include one official request-management UI so the operator surface is not limited to direct admin apps only.

#### Scenario: The media request UI is rendered

- **WHEN** the official media stack is rendered
- **THEN** `Seerr` MUST be deployed in the `media` namespace with persistent config storage
- **AND** the official public UI catalog MUST publish its route
- **AND** Homepage MUST render the `Seerr` card under the `Media` group

### Requirement: Media post-install is a supported rerunnable phase

The operator surface MUST expose media-specific post-install reconciliation without bloating the main Taskfile or relying on hidden one-off commands.

#### Scenario: Media post-install runs after GitOps bootstrap

- **WHEN** the operator runs `task up` or explicitly runs the media post-install task
- **THEN** the repo MUST execute a dedicated `media:post-install` task from a separate Taskfile
- **AND** that task MUST validate the expected media workloads
- **AND** it MUST reuse the supported downloader bootstrap path instead of duplicating downloader logic inline

#### Scenario: VPN-backed downloader prerequisites are missing

- **WHEN** the downloader path cannot be reconciled because the required ProtonVPN-backed credentials are absent or unusable
- **THEN** the media post-install phase MUST fail closed
- **AND** the operator output MUST identify the VPN/downloader prerequisite as the blocker

### Requirement: Media observability only claims supported metrics

The repo MUST surface media metrics only for services that have a supported native or explicit exporter path.

#### Scenario: Supported media metrics are scraped

- **WHEN** a repo-managed media service exposes native Prometheus metrics or a declared exporter
- **THEN** Prometheus MUST scrape that service through repo-managed discovery
- **AND** Grafana MUST expose a repo-managed dashboard for that media metrics surface

#### Scenario: A service has no supported app metrics

- **WHEN** a repo-managed media service does not expose native Prometheus metrics and the repo does not intentionally ship an exporter for it
- **THEN** the repo MUST NOT claim that the service has an application-metrics dashboard
- **AND** verification MAY treat browser availability as the supported observability surface for that service instead
