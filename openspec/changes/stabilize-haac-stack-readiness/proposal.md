## Why

`task up` no longer stalls in node configuration, but the workload readiness gate still fails because `haac-stack` stays degraded. Live cluster evidence shows two concrete blockers:

- `nvidia-device-plugin` crash-loops on the GPU workers unless the DaemonSet runs with `runtimeClassName: nvidia`, even though the worker runtime handler and cluster `RuntimeClass` already exist.
- `haac-gateway` is invalid because the Gateway listeners use ports `80/443` while the bundled Traefik entrypoints are still `8000/8443`, so Traefik rejects both listeners with `PortUnavailable`.

These are both workload-layer contract mismatches. They should be fixed declaratively in the chart so GitOps converges without live-only patches.

Live reconciliation also exposed a third workload-layer mismatch after the earlier fixes:

- the `downloaders` Deployment stays unready because `caseyscarborough/qbittorrent-exporter:1.3.0` no longer exists in the registry, so the exporter sidecar sits in `ErrImagePull`
- even after fixing the exporter image, the `downloaders` rollout can wedge because the default rolling strategy overlaps old and new qBittorrent pods against the same config volume; deleting the old pod lets the new pod become ready immediately

## What Changes

- Centralize the NVIDIA runtime class name under the shared chart values and use it for both GPU workloads and the NVIDIA device-plugin DaemonSet.
- Align the Gateway listener contract with the Traefik entrypoint ports actually exposed by the current K3s Traefik deployment, and drop the invalid in-cluster HTTPS listener that has no TLS configuration.
- Remove the non-standard Headlamp token-header bootstrap workaround that keeps blocking `haac-stack`, while retaining the remaining bootstrap Job on a rerunnable Argo pattern.
- Replace the dead qBittorrent exporter image pin with a live compatible image/tag and align the metrics port contract in the Deployment and Service.
- Make the `downloaders` Deployment use a recreate rollout so qBittorrent does not overlap old and new pods against the same config state during GitOps updates.
- Validate the fix by publishing the chart changes and verifying that `wait-for-stack` moves beyond the `haac-stack` gate.

## Impact

- `task up` should stop failing at the workload readiness gate for these known degradations.
- GPU runtime selection becomes more DRY: the chart has one source of truth for the NVIDIA runtime class.
- Gateway API health reflects the real Traefik entrypoint contract instead of staying degraded indefinitely.
