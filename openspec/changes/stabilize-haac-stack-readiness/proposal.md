## Why

`task up` no longer stalls in node configuration, but the workload readiness gate still fails because `haac-stack` stays degraded. Live cluster evidence shows two concrete blockers:

- `nvidia-device-plugin` crash-loops on the GPU workers unless the DaemonSet runs with `runtimeClassName: nvidia`, even though the worker runtime handler and cluster `RuntimeClass` already exist.
- `haac-gateway` is invalid because the Gateway listeners use ports `80/443` while the bundled Traefik entrypoints are still `8000/8443`, so Traefik rejects both listeners with `PortUnavailable`.

These are both workload-layer contract mismatches. They should be fixed declaratively in the chart so GitOps converges without live-only patches.

## What Changes

- Centralize the NVIDIA runtime class name under the shared chart values and use it for both GPU workloads and the NVIDIA device-plugin DaemonSet.
- Align the Gateway listener ports with the Traefik entrypoint ports actually exposed by the current K3s Traefik deployment.
- Validate the fix by publishing the chart changes and verifying that `wait-for-stack` moves beyond the `haac-stack` gate.

## Impact

- `task up` should stop failing at the workload readiness gate for these known degradations.
- GPU runtime selection becomes more DRY: the chart has one source of truth for the NVIDIA runtime class.
- Gateway API health reflects the real Traefik entrypoint contract instead of staying degraded indefinitely.
