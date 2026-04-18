## 1. OpenSpec and route catalog

- [x] 1.1 Add the OpenSpec deltas for the repo-managed `arr` stack surface and official `Seerr` route
- [x] 1.2 Add `Seerr` to the workload chart, values template, and public UI catalog

## 2. Media post-install surface

- [x] 2.1 Add a dedicated `Taskfile.media.yml` and wire `media:post-install` into the supported bootstrap path
- [x] 2.2 Extend `scripts/haac.py` with a rerunnable media reconcile command that validates media readiness and reuses the supported downloader bootstrap

## 3. Media observability

- [x] 3.1 Enable `FlareSolverr` Prometheus metrics and add `exportarr` metrics for `radarr`, `sonarr`, and `prowlarr`
- [x] 3.2 Add Prometheus scrape configuration plus a repo-managed Grafana dashboard for the supported media metrics

## 4. Verification and docs

- [x] 4.1 Extend tests and browser verification for `Seerr` plus the Grafana media dashboard surface
- [x] 4.2 Validate with OpenSpec, render gates, live GitOps/media reconciliation, and browser checks; then update the repo docs and task checklist
