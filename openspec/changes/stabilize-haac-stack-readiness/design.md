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

### 4. Make bootstrap Jobs rerunnable

The next live blocker after the GPU and Gateway fixes is Argo repeatedly trying to replace existing `Job` resources:

- `headlamp-token-bootstrap`
- `downloaders-bootstrap`

These Jobs currently use `argocd.argoproj.io/sync-options: Replace=true`, which is the wrong primitive for Kubernetes Jobs because selector/template fields are immutable once the Job exists.

The safer GitOps pattern here is:

- mark the Jobs as `PostSync` hooks
- add `argocd.argoproj.io/hook-delete-policy: BeforeHookCreation`
- remove `Replace=true`

That keeps the Jobs rerunnable on later syncs while preventing immutable-field failures from blocking the whole application.
