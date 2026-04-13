## ADDED Requirements

### Requirement: OpenTofu uses supported Proxmox provider APIs
The OpenTofu configuration MUST use and preserve the supported Proxmox provider datastore and download-file object names so normal bootstrap runs do not emit provider deprecation warnings for core infrastructure discovery and template download.

#### Scenario: Datastore lookup avoids deprecated datasource names
- **WHEN** OpenTofu initializes and plans or applies the Proxmox infrastructure
- **THEN** the datastore lookup MUST use `proxmox_datastores` instead of the deprecated `proxmox_virtual_environment_datastores`

#### Scenario: Template download avoids deprecated resource names
- **WHEN** OpenTofu initializes and plans or applies the Proxmox infrastructure
- **THEN** the Debian template download MUST use `proxmox_download_file` instead of the deprecated `proxmox_virtual_environment_download_file`
