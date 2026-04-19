## ADDED Requirements

### Requirement: Downloader bootstrap uses the real in-pod readiness contract

The downloader bootstrap MUST treat the same-pod qBittorrent and QUI API contract as the authoritative readiness surface for the repo-managed ARR stack.

#### Scenario: qBittorrent is authenticated-ready inside the downloader pod

- **WHEN** qBittorrent exposes its WebUI API in an authenticated-ready state and `/api/v2/app/version` returns `403`
- **AND** QUI already answers `/api/auth/me`
- **THEN** the supported downloader bootstrap MUST continue into the qBittorrent login reconciliation and QUI instance upsert flow instead of timing out before bootstrap begins

#### Scenario: qBittorrent login reconciliation remains the hard gate

- **WHEN** the downloader bootstrap proceeds past the early readiness check
- **THEN** it MUST still fail if qBittorrent does not accept the reconciled password
- **AND** it MUST still fail if QUI cannot report a connected qBittorrent instance before timeout

### Requirement: ProtonVPN blocker reporting is evidence-based

Media bootstrap MUST only report a ProtonVPN-specific prerequisite failure when recent Gluetun evidence proves a real VPN-side blocker.

#### Scenario: healthy Gluetun logs do not trigger a false Proton blocker

- **WHEN** Gluetun reaches its OpenVPN initialization sequence and port-forwarding steady state
- **AND** the actual downloader bootstrap fails for a different reason such as a local API readiness mismatch
- **THEN** the media bootstrap failure MUST surface the downloader error itself
- **AND** it MUST NOT claim that the ProtonVPN subscription or credentials are invalid

#### Scenario: real Proton auth or port-forwarding failures remain explicit

- **WHEN** recent Gluetun logs show concrete provider-side failures such as authentication rejection, missing subscription entitlement, or port-forwarding refusal
- **THEN** the media bootstrap failure MUST report that ProtonVPN-backed prerequisite problem explicitly
