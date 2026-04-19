## Why

The repo-managed media stack now bootstraps and exposes the expected admin/request surfaces, but there is still no supported proof that a real request can traverse the whole path:

- `Seerr` request creation
- `Prowlarr` indexer search
- `FlareSolverr` challenge solving when required
- `qBittorrent` through ProtonVPN/Gluetun
- import into the shared NAS-backed media path
- library visibility in `Jellyfin`

Live evidence on April 19, 2026 shows the stack is close but not yet productized as an end-to-end verifier:

- `task up` and `media:post-install` pass, and the media apps are reachable
- the NAS mount is real and shared into the media workloads
- `Prowlarr` can search a live public indexer through `FlareSolverr`
- `Seerr` can create a request in `Radarr`
- but the repo does not yet ship a rerunnable verifier that proves a safe title can reach the downloader, land on NAS, import, and become visible in Jellyfin

That matters because the current operator contract can say the stack is healthy even when the last-mile media path is only assumed.

## What Changes

- Add one explicit end-to-end media verification command and task that is safe to rerun and is not part of `task up`.
- Verify the downloader path through the repo-managed `qBittorrent` + ProtonVPN/Gluetun topology instead of assuming the ARR download client wiring is enough.
- Use a curated safe-title strategy for the verifier so the round can avoid copyrighted or ambiguous test content and fail with a concrete blocker when no suitable test source exists.
- Prove that imported media lands on the NAS-backed shared path and becomes queryable from Jellyfin.

## Capabilities

### Added Capabilities

- `arr-download-verification`

## Impact

- Affected code lives in `Taskfile.yml`, `Taskfile.internal.yml`, `scripts/haac.py`, `tests/test_haac.py`, and `openspec/`.
- Verification must include OpenSpec validation, targeted Python tests, dry-run bootstrap, live media verification against the real cluster, and browser/API checks where the flow reaches public surfaces.
- This wave stays narrow:
  - it does not make `task up` download content automatically
  - it does not promise every tracker or every title will work
  - it fails closed with a concrete blocker when no safe seeded candidate or no usable indexer/downloader path exists
