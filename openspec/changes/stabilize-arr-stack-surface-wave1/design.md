## Design

### Scope boundary

This wave is about making the existing repo-managed `arr` stack feel like one operator surface instead of a pile of adjacent pods.

It therefore covers four narrow layers together:

1. a request-management UI (`Seerr`)
2. a supported media post-install entrypoint
3. supported observability surfaces for media services with real metrics
4. verification that those surfaces are actually reachable

It does not attempt a full first-run automation of every media application, because several of those applications still keep part of their stateful setup inside their own persistent config stores and UIs.

### Seerr shape

The upstream Seerr chart documents Seerr as a stateful single-instance application and ships Kubernetes defaults such as:

- a persistent config volume
- a non-root security context
- readiness and liveness based on the app surface

This repo already manages the rest of the media stack inside the `haac-stack` Helm chart, so wave1 keeps that topology and adds a repo-managed `StatefulSet`/service pair for `Seerr` inside the existing media chart rather than introducing a second Helm release just for one media UI.

The deployment should follow the stable upstream behavior shape:

- one replica only
- persistent config storage
- non-root security context where practical
- probes on `/api/v1/settings/public`, which the official Docker documentation already uses as the health command
- a stable `API_KEY` environment variable sourced from `.env`

Because the upstream project does not expose native Prometheus metrics or a `ServiceMonitor` surface, wave1 treats Seerr as a browser-facing app only, not a fake application-metrics target.

### Media post-install boundary

The current repo already has:

- `security:post-install`
- `chaos:post-install`

Wave1 adds the missing sibling:

- `media:post-install`

That task lives in a separate `Taskfile.media.yml` so the user request to avoid bloating the main Taskfile remains respected.

The first supported media post-install path will stay deliberately narrow:

- verify that the required media workloads are reachable through the cluster session
- reconcile the existing qBittorrent/QUI bootstrap through the already-supported downloader bootstrap command
- verify that the media support surfaces needed by this wave (`Seerr`, `FlareSolverr`, `exportarr`) are present after reconciliation

This keeps the imperative bridge small and rerunnable without inventing a second hidden media bootstrap path.

### Metrics and dashboards

Wave1 only publishes metrics when a supported source exists:

- `qBittorrent` already has a repo-managed exporter and ServiceMonitor
- `FlareSolverr` supports native Prometheus metrics through `PROMETHEUS_ENABLED` and `PROMETHEUS_PORT`
- `exportarr` supports `radarr`, `sonarr`, and `prowlarr`, and can read each app API key from the colocated `config.xml`

The repo will therefore:

- enable FlareSolverr metrics in the existing deployment and service
- add `exportarr` sidecars to `radarr`, `sonarr`, and `prowlarr`
- extend each corresponding service with a metrics port
- add Prometheus `ServiceMonitor` objects for those metric surfaces
- add one repo-managed Grafana dashboard ConfigMap for the `arr` stack

`exportarr` is explicitly a third-party exporter in maintenance mode, so wave1 treats it as an observability improvement, not as a canonical product API. The design therefore prefers sidecars over copied API keys in Git-managed secrets, keeps the collector scope limited to `radarr`, `sonarr`, and `prowlarr`, and documents the tradeoff in the change itself.

### Verification

- `openspec validate stabilize-arr-stack-surface-wave1`
- `python scripts/haac.py check-env`
- `python scripts/haac.py doctor`
- `python scripts/haac.py task-run -- -n up`
- `python -m py_compile scripts/haac.py scripts/haac_loop.py scripts/hydrate-authelia.py`
- `python -m unittest discover -s tests -p "test_haac.py" -v`
- `helm template haac-stack k8s/charts/haac-stack`
- `kubectl kustomize k8s/bootstrap/root`
- `kubectl kustomize k8s/platform`
- `kubectl kustomize k8s/workloads`
- `python scripts/haac.py task-run -- reconcile:gitops`
- `python scripts/haac.py task-run -- media:post-install`
- `python scripts/haac.py task-run -- wait-for-argocd-sync`
- browser verification for `Homepage`, `Seerr`, and the Grafana media dashboard surface

### Recovery and rollback

- rerunning `task media:post-install` is the supported recovery path for partial media bootstrap failures after GitOps is already healthy
- rerunning `task up` remains the full supported recovery path for end-to-end bootstrap
- removing the wave reverts to the pre-existing media stack:
  - delete the `Seerr` workload
  - remove the media post-install task
  - remove the added metrics sidecars and ServiceMonitors
  - remove the Grafana dashboard ConfigMap
- if the downloader path cannot come up because the ProtonVPN credentials are absent or the subscription is unusable, the wave must fail closed and report that blocker explicitly instead of pretending the media stack is healthy
