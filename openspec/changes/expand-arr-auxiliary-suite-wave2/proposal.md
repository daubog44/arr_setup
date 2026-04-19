## Why

The core movies/TV ARR surface is now live, browser-verified, and VPN-backed, but the broader media automation suite is still narrower than the operator asked for.

Evidence on April 19, 2026:

- the current repo-managed stack covers Jellyfin, Seerr, Radarr, Sonarr, Prowlarr, qBittorrent/QUI, Bazarr, Unpackerr, Autobrr, FlareSolverr, and Recyclarr
- `geekau/mediastack` still treats Lidarr, SABnzbd, Tdarr, Mylar, and other auxiliary media apps as first-class stack members, but marks Huntarr as deprecated in the current README
- official Seerr docs emphasize stable media-server internal URLs and owner-account automation, which aligns with the repo-managed Seerr bootstrap surface already in place
- the current repo has no repo-managed manifests or post-install automation for Lidarr or SABnzbd, and no Grafana metric surface for those additions

## What Changes

- Add a repo-managed auxiliary media wave centered on `Lidarr` and `SABnzbd`, with Homepage, ingress, storage, and API bootstrap wired to the existing Prowlarr/Jellyfin/Seerr posture.
- Extend the media post-install surface so Lidarr and SABnzbd are configured automatically with repo-managed download-client and indexer relationships.
- Add Prometheus/Grafana visibility for the newly supported services when they expose metrics directly or through a supported exporter.
- Document the app-selection rationale explicitly, including why deprecated or weak-signal candidates such as Huntarr are deferred from the first supported wave.

## Capabilities

### New Capabilities
- `arr-auxiliary-suite`: Define the supported repo-managed auxiliary media services beyond the core movies/TV ARR surface.

### Modified Capabilities
- `arr-best-practice-automation`: The supported media bootstrap may include additional repo-managed acquisition and library services when their API bootstrap and observability surfaces are explicit.

## Impact

- Affected code will primarily live in `k8s/charts/haac-stack/charts/media`, `k8s/charts/haac-stack/config-templates/values.yaml.template`, `scripts/haac.py`, `tests/test_haac.py`, Homepage/Grafana assets, and repo docs.
- Validation must include OpenSpec, focused unit coverage, Helm/Kustomize render checks, a live `media:post-install` rerun, and browser verification of any new public surfaces.
