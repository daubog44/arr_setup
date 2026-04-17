## MODIFIED Requirements

### Requirement: Falco homelab rules are high-signal

The repo-managed Falco host rule bundle MUST favor high-signal host activity over noisy localhost-only probes.

#### Scenario: Loopback socket probe runs on the Proxmox host

- **WHEN** a loopback-only probe uses `nc`, `ncat`, or `socat` against `localhost` or `127.0.0.1`
- **THEN** the custom HAAC socket-tool rule MUST NOT emit a warning for that event
- **AND** non-loopback socket tooling MUST continue to be surfaced as a warning
