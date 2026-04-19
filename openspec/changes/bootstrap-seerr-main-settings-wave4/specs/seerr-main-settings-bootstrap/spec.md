## ADDED Requirements

### Requirement: Seerr persists the repo-managed public application URL
The media post-install bootstrap MUST keep Seerr's main settings aligned with the repo-managed public service URL.

#### Scenario: Seerr is initialized but still keeps an empty application URL
- **WHEN** `media:post-install` reaches the Seerr bootstrap stage
- **AND** Seerr already exposes an initialized public request surface
- **BUT** the main settings still leave `applicationUrl` empty or stale
- **THEN** the bootstrap MUST persist `https://seerr.<domain>` through Seerr's supported admin settings API
- **AND** reruns MUST keep the setting idempotent instead of requiring manual UI edits
