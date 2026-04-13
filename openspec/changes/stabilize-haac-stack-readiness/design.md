## Design

### 1. Centralize the NVIDIA runtime class

The repo already configures the worker-side `nvidia` runtime handler and the cluster already exposes a `RuntimeClass` named `nvidia`. The remaining mismatch is chart-side:

- `jellyfin` already opts into `runtimeClassName: nvidia`
- `nvidia-device-plugin` does not

The chart should expose a single value under `global.scheduling.gpu.nvidiaRuntimeClassName` and consume it in both templates. That keeps GPU runtime selection centralized and avoids another hardcoded `nvidia` string.

### 2. Align the Gateway listener contract with Traefik

Live Traefik args show:

- `--entryPoints.web.address=:8000/tcp`
- `--entryPoints.websecure.address=:8443/tcp`

Traefik Gateway API marks the current Gateway invalid because:

- the listeners originally asked for `80/443` instead of the active Traefik entrypoint ports
- the in-cluster `HTTPS` listener has no TLS configuration at all

Because Cloudflare already terminates public TLS for this homelab, the cluster-side Gateway only needs the HTTP listener. The smallest safe fix is therefore:

- align the HTTP listener with the active Traefik `web` entrypoint port
- remove the invalid in-cluster HTTPS listener instead of inventing TLS state the cluster is not meant to own

### 3. Validation

Validation should prove the fix in the actual bootstrap path:

- render the chart locally
- publish the chart changes to the GitOps repo
- verify `nvidia-device-plugin` stays healthy without the live-only patch
- verify `haac-gateway` becomes accepted
- rerun `wait-for-stack` and record the next verified phase

### 4. Simplify the remaining bootstrap surface

The next live blocker after the GPU and Gateway fixes is the custom Headlamp bootstrap path. The repo currently adds:

- an explicit `headlamp-admin-token` secret
- a `headlamp-token-bootstrap` Job
- a `headlamp-token-header` Traefik middleware injected through the route values

That workaround is not part of the normal Headlamp in-cluster deployment model, and in live evidence it is the resource Argo keeps waiting on even after the Job object disappears from the cluster. The safer path is to remove that non-standard bootstrap branch entirely and keep Headlamp on the standard in-cluster service account path it already has through `serviceAccountName: headlamp-admin`.

The remaining downloader bootstrap can stay, but it should use the ArgoCD rerunnable Job pattern:

- keep them as normal resources rather than hooks
- set `argocd.argoproj.io/sync-options: Force=true,Replace=true`

That keeps the genuinely needed bootstrap job rerunnable without letting an unnecessary Headlamp workaround block the whole application.

### 5. Align QUI with the deployed auth model

Live evidence shows the shipped QUI version no longer supports the bootstrap contract currently encoded in the repo:

- the chart enables internal OIDC inside QUI
- the bootstrap paths still call `/api/auth/setup`, `/api/auth/login`, and `/api/download_clients`
- the public `qui` route is already behind the cluster's Authelia forward-auth layer

That creates an impossible state where QUI reports both "initial setup required" and "setup disabled when OIDC is enabled". The smallest coherent fix is:

- remove QUI from Authelia's OIDC client list
- disable QUI's internal OIDC in the chart
- enable QUI's documented auth-disabled mode, scoped to loopback plus the cluster pod/service CIDRs
- keep public protection at the ingress layer through Authelia
- update both the in-cluster bootstrap Job and the manual fallback path to reconcile qBittorrent through `/api/instances`

This keeps the operator-visible auth model unchanged while making the workload-layer bootstrap match the actual QUI API surface.
