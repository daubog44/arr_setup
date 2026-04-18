## ADDED Requirements

### Requirement: The first ARR suite expansion is repo-managed

The repo-managed ARR stack MUST include the first expansion apps that materially improve the current movies/TV flow without introducing unrelated provider domains.

#### Scenario: Bazarr is part of the supported media surface

- **WHEN** the media stack is enabled
- **THEN** Bazarr MUST be deployed as part of the repo-managed workload surface
- **AND** it MUST be reachable through the declared ingress catalog

#### Scenario: Unpackerr complements the downloader path

- **WHEN** the downloader stack is enabled
- **THEN** Unpackerr MUST be configured against the repo-managed downloader and ARR topology so extracted downloads can converge without manual sidecar setup

### Requirement: Expanded media services are verified through real signals

Expanded media services MUST be verified through native metrics where they exist, or through live reachability when they do not.

#### Scenario: A new service exposes metrics

- **WHEN** Bazarr or Unpackerr exposes native metrics or a safe exporter path
- **THEN** the repo MUST wire that signal into Prometheus and verify it in Grafana

#### Scenario: A new service does not expose metrics

- **WHEN** a newly added media service has no safe metrics endpoint
- **THEN** the verification flow MUST still check the service through HTTP and browser-level reachability
