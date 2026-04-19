## Why

The media stack is now live and API-wired, but several of the supported `*arr` services still keep weak stock defaults that do not match the repo's stated "best practice" posture.

Live evidence captured on April 19, 2026 from the repo-managed cluster:

- `Radarr` still reports `renameMovies=false`, `deleteEmptyFolders=false`, `setPermissionsLinux=false`, and `chmodFolder=755`
- `Sonarr` still reports `renameEpisodes=false`, `deleteEmptyFolders=false`, `setPermissionsLinux=false`, and `chmodFolder=755`
- `Lidarr` still reports `renameTracks=false`, `deleteEmptyFolders=false`, `setPermissionsLinux=false`, and `chmodFolder=755`
- the repo bootstrap already wires download clients, Prowlarr, Bazarr, Seerr, Jellyfin, and Recyclarr, so the remaining gap is the "common settings" layer rather than first-run connectivity
- MediaStack.Guide still documents shared `*arr` defaults such as renaming enabled, hardlinks enabled, empty-folder cleanup enabled, and Linux permissions set to `775`
- the current repo-managed Jellyfin bootstrap only guarantees Movies and TV libraries even though the supported suite now includes Lidarr-managed music

The operator asked for a full ARR setup with best-practice settings and a stronger Jellyfin experience. The next wave should therefore make the existing supported apps opinionated and rerunnable before adding more adjacent services.

## What Changes

- Extend `media:post-install` so Radarr, Sonarr, and Lidarr reconcile a repo-managed common settings baseline through their supported APIs.
- Extend the Jellyfin bootstrap so the supported media surface includes the Lidarr music library by default.
- Document the curated supported suite and the rationale for deferring adjacent apps that still need a separate lifecycle decision, such as deprecated or unstable `Readarr` packaging.

## Capabilities

### New Capabilities

- `arr-common-settings-bootstrap`: Define the repo-managed common settings baseline for supported ARR library managers.

### Modified Capabilities

- `arr-best-practice-automation`: The supported rerun surface now includes API reconciliation of common ARR settings, not only connectivity and quality profiles.
- `arr-stack-surface`: The supported Jellyfin bootstrap includes the music library when the Lidarr surface is part of the stack.

## Impact

- Affected code will live primarily in [scripts/haac.py](/C:/Users/Utente/OneDrive%20-%20ITS%20Tech%20Talent%20Factory/Desktop/dev/arr_setup-main/scripts/haac.py), [tests/test_haac.py](/C:/Users/Utente/OneDrive%20-%20ITS%20Tech%20Talent%20Factory/Desktop/dev/arr_setup-main/tests/test_haac.py), and [README.md](/C:/Users/Utente/OneDrive%20-%20ITS%20Tech%20Talent%20Factory/Desktop/dev/arr_setup-main/README.md).
- Verification must include OpenSpec validation, targeted unit coverage, Helm and Kustomize render checks, a live `task media:post-install` rerun, API evidence for the reconciled settings, and browser verification of the public media surfaces.
