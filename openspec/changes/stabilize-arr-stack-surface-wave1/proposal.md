## Why

The repo already deploys the core media automation path, but it is still not a coherent repo-managed `arr` product.

Live evidence on April 18, 2026 shows:

- `media` already runs `radarr`, `sonarr`, `prowlarr`, `autobrr`, `qBittorrent/QUI`, `flaresolverr`, and `jellyfin`, and ArgoCD reports the stack `Synced Healthy`
- the only media Prometheus surface currently wired into Grafana is the qBittorrent exporter
- there is no repo-managed request UI such as `Seerr`
- the only supported imperative media bootstrap path is the downloader bootstrap hidden behind `configure-apps`, not an explicit post-install phase
- the official `Seerr` chart exists upstream, but the upstream chart does not expose a native Prometheus or ServiceMonitor surface
- upstream `FlareSolverr` supports Prometheus metrics, but the current repo deployment does not enable them
- upstream `exportarr` exists for `radarr`, `sonarr`, and `prowlarr`, but the current repo does not expose those app metrics into Prometheus/Grafana

That gap matters because `task up` currently lands a set of reachable media apps, but not a productized `arr` stack with request management, explicit post-install reconciliation, or verified media observability.

## What Changes

- Add `Seerr` as a first-class repo-managed media UI in the workload chart and official route catalog.
- Add a dedicated `media` post-install surface in its own Taskfile so media reconciliation does not expand the main Taskfile or hide in ad-hoc commands.
- Turn the existing downloader bootstrap into part of the supported media post-install path.
- Expose supported media metrics:
  - `FlareSolverr` native Prometheus metrics
  - `exportarr` sidecars for `radarr`, `sonarr`, and `prowlarr`
  - Grafana dashboards for the repo-managed media metrics that actually exist
- Extend verification so browser checks cover `Seerr`, and Grafana checks cover the media dashboards added by this wave.

## Capabilities

### Added Capabilities

- `arr-stack-surface`

### Modified Capabilities

- `public-ui-surface`

## Impact

- Affected code lives in `Taskfile.yml`, a new `Taskfile.media.yml`, `scripts/haac.py`, `scripts/verify-public-auth.mjs`, `tests/test_haac.py`, `k8s/charts/haac-stack/`, and `k8s/platform/observability/`.
- Verification must include OpenSpec validation, dry-run/render gates, live media reconciliation, live ArgoCD health, and browser checks for both public media UIs and Grafana media dashboards.
- The wave stays narrow:
  - it does not invent app metrics for services that do not expose them
  - it does not require full Seerr-to-Jellyfin first-run automation
  - it may stop only if the downloader path cannot be reconciled because the required ProtonVPN subscription-backed credentials are absent or invalid
