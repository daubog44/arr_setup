## Why

`task up` no longer stalls in node configuration, but the workload readiness gate still fails because `haac-stack` stays degraded. Live cluster evidence shows two concrete blockers:

- `nvidia-device-plugin` crash-loops on the GPU workers unless the DaemonSet runs with `runtimeClassName: nvidia`, even though the worker runtime handler and cluster `RuntimeClass` already exist.
- `haac-gateway` is invalid because the Gateway listeners use ports `80/443` while the bundled Traefik entrypoints are still `8000/8443`, so Traefik rejects both listeners with `PortUnavailable`.

These are both workload-layer contract mismatches. They should be fixed declaratively in the chart so GitOps converges without live-only patches.

Live reconciliation also exposed a third workload-layer mismatch after the earlier fixes:

- the `downloaders` Deployment stays unready because `caseyscarborough/qbittorrent-exporter:1.3.0` no longer exists in the registry, so the exporter sidecar sits in `ErrImagePull`
- even after fixing the exporter image, the `downloaders` rollout can wedge because the default rolling strategy overlaps old and new qBittorrent pods against the same config volume; deleting the old pod lets the new pod become ready immediately
- the remaining `downloaders-bootstrap` Job can still crash-loop because its pod-name discovery relies on external text utilities that are not guaranteed to exist in the chosen image, even though the Kubernetes API response itself is sufficient
- after those fixes, the remaining `downloaders-bootstrap` logic still targets legacy QUI auth and client APIs (`/api/auth/setup`, `/api/auth/login`, `/api/download_clients`) that no longer match the shipped QUI version, while the chart simultaneously enables OIDC inside QUI even though the public route is already protected by Authelia
- live cluster verification shows a more fundamental downloader bootstrap mismatch: qBittorrent's WebUI API returns `403` to the separate bootstrap pod on `qbittorrent.media.svc.cluster.local:8080`, so a cross-pod Job cannot reliably reconcile qBittorrent credentials in the first place

## What Changes

- Centralize the NVIDIA runtime class name under the shared chart values and use it for both GPU workloads and the NVIDIA device-plugin DaemonSet.
- Align the Gateway listener contract with the Traefik entrypoint ports actually exposed by the current K3s Traefik deployment, and drop the invalid in-cluster HTTPS listener that has no TLS configuration.
- Remove the non-standard Headlamp token-header bootstrap workaround that keeps blocking `haac-stack`, while retaining the remaining bootstrap Job on a rerunnable Argo pattern.
- Replace the dead qBittorrent exporter image pin with a live compatible image/tag and align the metrics port contract in the Deployment and Service.
- Make the `downloaders` Deployment use a non-overlapping rolling strategy (`maxSurge: 0`, `maxUnavailable: 1`) so qBittorrent state does not wedge readiness during GitOps updates.
- Remove QUI's redundant internal OIDC dependency, keep QUI protected by the existing Authelia forward-auth layer, and reconcile the qBittorrent instance through the supported `/api/instances` API instead of the dead legacy endpoints.
- Move downloader bootstrap into the `port-sync` sidecar inside the `downloaders` pod so qBittorrent and QUI are reached over `127.0.0.1` while the sidecar reuses a narrow Kubernetes API permission only for qBittorrent log inspection.
- Validate the fix by publishing the chart changes and verifying that `wait-for-stack` moves beyond the `haac-stack` gate.

## Impact

- `task up` should stop failing at the workload readiness gate for these known degradations.
- GPU runtime selection becomes more DRY: the chart has one source of truth for the NVIDIA runtime class.
- Gateway API health reflects the real Traefik entrypoint contract instead of staying degraded indefinitely.
- Downloader bootstrap becomes version-coherent with the current QUI image and no longer depends on a self-contradictory `setup required` plus `OIDC enabled` state.
- The bootstrap path no longer depends on a separate Job that qBittorrent can reject on host-header or cross-pod API rules.
