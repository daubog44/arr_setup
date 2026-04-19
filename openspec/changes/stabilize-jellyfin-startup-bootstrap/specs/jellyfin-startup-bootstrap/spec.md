## ADDED Requirements

### Requirement: Jellyfin first-run state is bootstrapped before Seerr login

The media post-install bootstrap MUST prepare Jellyfin for Seerr when Jellyfin still exposes its first-run startup surface.

#### Scenario: Jellyfin startup wizard is incomplete

- **WHEN** Jellyfin reports `StartupWizardCompleted=false`
- **THEN** media post-install MUST create or update the initial admin user through the supported startup endpoints
- **AND** it MUST complete the Jellyfin startup wizard before Seerr authentication is attempted

#### Scenario: Existing Jellyfin installs are left intact

- **WHEN** Jellyfin already reports `StartupWizardCompleted=true`
- **THEN** media post-install MUST NOT reset the existing Jellyfin admin automatically
- **AND** later auth failures MUST surface as credential mismatches rather than forcing a reset
