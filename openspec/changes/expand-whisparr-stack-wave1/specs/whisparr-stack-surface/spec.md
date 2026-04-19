## ADDED Requirements

### Requirement: Whisparr is repo-managed as a separate media surface

The repo MUST support Whisparr as a standalone media-management workload with the same shared NAS and downloader topology conventions used by the rest of the stack.

#### Scenario: Media post-install configures Whisparr

- **WHEN** the operator deploys the stack with Whisparr enabled
- **THEN** the repo MUST reconcile a supported root folder, download-client wiring, and Prowlarr application linkage for Whisparr
- **AND** it MUST keep Whisparr on a dedicated category and media root to avoid collisions with movie, TV, and music imports

