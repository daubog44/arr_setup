## Why

The repository now contains a large amount of bootstrap, media, security, and GitOps behavior, but the operator documentation still lives mostly in `README.md` and narrow runbooks. The operator explicitly wants detailed documentation for the tools, codebase, media flow, and security surfaces.

## What Changes

- Add dedicated documentation for the media stack, security stack, and bootstrap codebase boundaries.
- Explain how Seerr, Prowlarr, Radarr, Sonarr, Lidarr, qBittorrent, and Jellyfin interact in this repo.
- Document the environment-variable surfaces, generated outputs, and the expected rerun paths.
- Add docs for any new CrowdSec and Whisparr behavior introduced by adjacent waves.

## Capabilities

### New Capabilities
- `operator-and-media-docs`: Detailed repository docs for bootstrap, media automation, and security topology.

### Modified Capabilities
- `task-up-bootstrap`: The operator contract docs must point to the detailed references instead of leaving complex surfaces implicit.

## Impact

- Affected code lives in `README.md`, `docs/`, and any spec or runbook references that currently assume tribal knowledge.
- Validation includes doc review against the implemented repo surfaces and command paths.
