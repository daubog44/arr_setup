## Why

`media:post-install` now progresses past downloader bootstrap, ARR ping checks, Seerr Jellyfin auth, and Jellyfin library sync, but it still fails while wiring Seerr to Radarr/Sonarr because the services expose no root folders to Seerr.

Live validation on April 18, 2026 showed:

- Seerr `/api/v1/settings/radarr/test` and `/api/v1/settings/sonarr/test` return populated `profiles`, but `rootFolders=[]`
- direct `POST /api/v3/rootfolder` to Radarr with `/data/movies` fails `PathExistsValidator`
- direct `POST /api/v3/rootfolder` to Sonarr with `/data/tv` fails `PathExistsValidator`
- the same official endpoint succeeds with `/data/media/movies` for Radarr and `/data/media/tv` for Sonarr

This means the ARR stack already has a usable shared media topology, but the post-install flow does not bootstrap the supported root folders before Seerr tries to consume them.

## What Changes

- Add an idempotent Radarr/Sonarr root-folder bootstrap step before Seerr requests ARR integration options.
- Encode the supported ARR media paths explicitly in the bootstrap code.
- Add regression coverage for create-if-missing and already-present root-folder behavior.

## Capabilities

### New Capabilities

- `arr-root-folder-bootstrap`: Define the supported Radarr and Sonarr root folders for the repo-managed ARR topology.

### Modified Capabilities

- `arr-stack-surface`: Media post-install must bootstrap ARR root folders before Seerr consumes ARR settings.

## Impact

- Affected code lives in [scripts/haac.py](C:/Users/Utente/OneDrive%20-%20ITS%20Tech%20Talent%20Factory/Desktop/dev/arr_setup-main/scripts/haac.py) and [tests/test_haac.py](C:/Users/Utente/OneDrive%20-%20ITS%20Tech%20Talent%20Factory/Desktop/dev/arr_setup-main/tests/test_haac.py).
- Verification must include OpenSpec validation, targeted Python unit tests, and a live `media:post-install` rerun that progresses beyond Seerr ARR option discovery.
