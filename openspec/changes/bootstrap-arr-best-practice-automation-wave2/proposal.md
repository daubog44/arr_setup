## Why

The movies/TV ARR stack is now reachable and browser-verified, but the downloader contract is still lighter than the operator asked for.

Live evidence on April 19, 2026:

- qBittorrent now persists the shared save and temp paths under `/data/torrents`
- the stack already bootstraps Radarr, Sonarr, Prowlarr, Seerr, Jellyfin, Bazarr, Unpackerr, and Recyclarr through API-driven post-install logic
- however qBittorrent still lacks repo-managed category definitions and category save paths for the ARR clients, so the stack relies on implicit downloader defaults instead of an explicit best-practice contract

The user also asked for a more opinionated, documented ARR setup aligned with TRaSH-style automation and reusable post-install logic.

## What Changes

- Add repo-managed qBittorrent category bootstrap through the supported WebUI API so the downloader owns explicit save paths for the ARR categories it already receives from Radarr, Sonarr, and Prowlarr.
- Extend media post-install verification to assert the qBittorrent category contract alongside the existing ARR, Seerr, Jellyfin, Bazarr, Unpackerr, and Recyclarr checks.
- Document the supported ARR automation surface and the environment variables that tune it.

## Capabilities

### New Capabilities
- `arr-best-practice-automation`: Define the supported post-install policy contract for the repo-managed movies/TV ARR stack.

### Modified Capabilities
- `downloaders-shared-paths`: The supported downloader surface must include explicit qBittorrent category routing for repo-managed ARR clients, not only a default save/temp path.

## Impact

- Affected code will primarily live in [scripts/haac.py](C:/Users/Utente/OneDrive%20-%20ITS%20Tech%20Talent%20Factory/Desktop/dev/arr_setup-main/scripts/haac.py), [k8s/charts/haac-stack/charts/downloaders/templates/downloaders.yaml](C:/Users/Utente/OneDrive%20-%20ITS%20Tech%20Talent%20Factory/Desktop/dev/arr_setup-main/k8s/charts/haac-stack/charts/downloaders/templates/downloaders.yaml), [tests/test_haac.py](C:/Users/Utente/OneDrive%20-%20ITS%20Tech%20Talent%20Factory/Desktop/dev/arr_setup-main/tests/test_haac.py), and operator docs such as [README.md](C:/Users/Utente/OneDrive%20-%20ITS%20Tech%20Talent%20Factory/Desktop/dev/arr_setup-main/README.md).
- Verification must include OpenSpec validation, focused unit coverage, a live `media:post-install` rerun, direct qBittorrent API evidence, and browser verification of the existing public media surfaces.
