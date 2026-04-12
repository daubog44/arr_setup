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

Traefik Gateway API marks the current Gateway invalid because the listeners ask for `80/443`. The smallest safe fix is to align the Gateway manifest with the active Traefik entrypoint ports used by the bundled K3s deployment. This is lower-risk than reshaping the bundled Traefik container ports during bootstrap.

### 3. Validation

Validation should prove the fix in the actual bootstrap path:

- render the chart locally
- publish the chart changes to the GitOps repo
- verify `nvidia-device-plugin` stays healthy without the live-only patch
- verify `haac-gateway` becomes accepted
- rerun `wait-for-stack` and record the next verified phase
