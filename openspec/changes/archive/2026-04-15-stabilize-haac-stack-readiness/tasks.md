## 1. Implementation

- [ ] 1.1 Add a shared Helm value for the NVIDIA runtime class and consume it in the GPU workload and NVIDIA device-plugin templates
- [ ] 1.2 Align the Gateway listener contract with the bundled Traefik entrypoints and remove the invalid in-cluster HTTPS listener
- [ ] 1.3 Remove the non-standard Headlamp token-header bootstrap path and keep only the bootstrap jobs that are still required
- [ ] 1.4 Replace the dead qBittorrent exporter image pin with a live compatible image/tag and align the metrics port contract
- [ ] 1.5 Make the `downloaders` Deployment use a non-overlapping rolling strategy so qBittorrent state does not wedge readiness during updates
- [ ] 1.6 Remove the standalone `downloaders-bootstrap` Job path and move downloader bootstrap into the `port-sync` sidecar with same-pod localhost access plus narrow Kubernetes log-read permissions
- [ ] 1.7 Remove QUI's internal OIDC bootstrap path, switch the workload to auth-disabled mode behind Authelia, and reconcile qBittorrent through `/api/instances`
- [ ] 1.8 Align the manual `configure-apps` fallback in `scripts/haac.py` with the same QUI `/api/instances` contract used by the in-cluster bootstrap Job

## 2. Validation

- [ ] 2.1 Validate with `helm template haac-stack k8s/charts/haac-stack`
- [ ] 2.2 Publish the GitOps changes and verify `nvidia-device-plugin` stays healthy without a live-only patch
- [ ] 2.3 Verify `haac-gateway` is accepted and rerun `python scripts/haac.py wait-for-stack ...` until it either passes `haac-stack` or fails on a later concrete gate
- [ ] 2.4 Verify the `downloaders` pod self-bootstrap now succeeds from same-pod localhost access and that `haac-stack` no longer waits on a standalone bootstrap Job
