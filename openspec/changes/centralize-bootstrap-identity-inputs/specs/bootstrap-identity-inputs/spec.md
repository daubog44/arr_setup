## ADDED Requirements

### Requirement: Main operator identity can seed service login defaults

The bootstrap env model MUST allow one main operator identity/password to seed supported service login defaults when no service-specific override is set.

#### Scenario: operator only provides the main identity layer

- **WHEN** `.env` defines the main operator identity and password
- **AND** supported service-specific login variables are unset
- **THEN** bootstrap MUST derive the supported service login defaults from the main identity layer
- **AND** the resulting secret generation and verification flows MUST stay deterministic
- **AND** lower-trust downloader local auth variables such as `QBITTORRENT_USERNAME` and `QUI_PASSWORD` MUST remain explicit unless the operator intentionally sets them

### Requirement: Per-service overrides still win over the main identity defaults

Service-specific login overrides MUST remain authoritative.

#### Scenario: operator sets both main identity defaults and a service-specific override

- **WHEN** the main identity layer is present
- **AND** a service-specific login variable is also present
- **THEN** bootstrap MUST prefer the explicit service-specific value for that service
- **AND** it MUST NOT overwrite the explicit override with the main default

### Requirement: Opaque application secrets stay independent

The main identity password MUST NOT become the default for unrelated machine secrets.

#### Scenario: bootstrap needs OIDC, cookie, encryption, or database secrets

- **WHEN** bootstrap reads `.env`
- **THEN** opaque application secrets MUST remain separate inputs
- **AND** documentation MUST distinguish them from human login defaults
