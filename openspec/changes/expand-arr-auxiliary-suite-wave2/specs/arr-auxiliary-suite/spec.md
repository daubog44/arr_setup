## ADDED Requirements

### Requirement: Auxiliary media services are repo-managed
The supported media stack MUST treat any promoted auxiliary service beyond the core movies/TV ARR surface as repo-managed, including its manifests, storage, bootstrap, and observability paths.

#### Scenario: Lidarr and SABnzbd are part of the supported auxiliary wave
- **WHEN** the active change enables auxiliary media services
- **THEN** the repo MUST render and publish repo-managed manifests for those services
- **AND** the operator MUST define their post-install and verification contract explicitly

### Requirement: Deprecated auxiliary candidates are not silently promoted
The operator MUST document when an auxiliary app from an external reference stack is intentionally deferred due to deprecation or weak support signal.

#### Scenario: Huntarr is referenced but deferred
- **WHEN** an external reference stack includes Huntarr
- **AND** the same reference marks it as deprecated
- **THEN** the repo MUST NOT silently add Huntarr as a first supported auxiliary service
- **AND** the change docs MUST record the reason for deferral
