## ADDED Requirements

### Requirement: CrowdSec must not ban supported operator traffic by default

The repo MUST suppress already-proven false positives for supported operator and media UI traffic without disabling the wider CrowdSec ingress protection posture.

#### Scenario: Generic 403-ban scenarios ignore declared operator UI traffic

- **WHEN** supported operator or media UI flows generate known-good `403` access-log events on declared paths
- **THEN** the repo-managed CrowdSec parser contract MUST prevent those events from feeding generic brute-force or `403`-abuse scenarios
- **AND** the operator IP MUST not be banned solely because of those declared paths

#### Scenario: AppSec allows declared homelab false-positive paths

- **WHEN** CrowdSec AppSec evaluates a request on a path already proven to false-positive for the supported homelab operator surface
- **THEN** the repo-managed custom AppSec config MUST allow that request and suppress the resulting alert
- **AND** AppSec MUST remain enabled for the broader ingress path
