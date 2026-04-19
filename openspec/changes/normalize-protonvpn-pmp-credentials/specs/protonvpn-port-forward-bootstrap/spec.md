## ADDED Requirements

### Requirement: ProtonVPN forwarding username ends in `+pmp`

The repo-managed ProtonVPN downloader secret MUST derive `OPENVPN_USER` from the operator input so that the final forwarding suffix ends in `+pmp`.

#### Scenario: Raw Proton username input

- **GIVEN** `.env` contains the raw Proton OpenVPN username without forwarding suffixes
- **WHEN** the repo generates the managed ProtonVPN secret
- **THEN** the resulting `OPENVPN_USER` MUST end in `+pmp`

#### Scenario: Legacy `+nr` input or generator state

- **GIVEN** a username shape that still includes `+nr`
- **WHEN** the repo normalizes the managed ProtonVPN forwarding username
- **THEN** the final generated username MUST omit `+nr`
- **AND** it MUST still end in `+pmp`
