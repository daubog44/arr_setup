## MODIFIED Requirements

### Requirement: Main operator identity can seed service login defaults

The bootstrap env model MUST allow one main operator identity/password to seed supported service login defaults when no service-specific override is set.

#### Scenario: operator only provides the main identity layer

- **WHEN** `.env` defines the main operator identity and password
- **AND** supported service-specific login variables are unset
- **THEN** bootstrap MUST derive the supported control-plane/admin login defaults from the main identity layer
- **AND** lower-trust downloader auth MUST remain separate unless the operator explicitly opts in to sharing it

### Requirement: Lower-trust app credential sharing is explicit

The bootstrap env model MUST treat downloader credential reuse as an explicit opt-in, not an implicit fallback.

#### Scenario: operator enables downloader credential sharing explicitly

- **WHEN** `.env` enables the supported downloader shared-credential flag
- **AND** the main operator username and password are present
- **THEN** qBittorrent and QUI MAY inherit those values when their dedicated downloader env vars are unset
- **AND** preflight or docs MUST make the widened blast radius explicit

#### Scenario: downloader credential sharing is not enabled

- **WHEN** the operator does not enable the downloader shared-credential flag
- **THEN** lower-trust downloader auth MUST remain explicit
- **AND** control-plane services such as Grafana MUST NOT fall back to downloader passwords
