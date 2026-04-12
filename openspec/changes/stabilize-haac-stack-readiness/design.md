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
