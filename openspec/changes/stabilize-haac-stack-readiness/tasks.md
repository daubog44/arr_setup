## 1. Implementation

- [ ] 1.1 Add a shared Helm value for the NVIDIA runtime class and consume it in the GPU workload and NVIDIA device-plugin templates
- [ ] 1.2 Align the Gateway listener contract with the bundled Traefik entrypoints and remove the invalid in-cluster HTTPS listener
- [ ] 1.3 Remove the non-standard Headlamp token-header bootstrap path and keep only the bootstrap jobs that are still required
- [ ] 1.4 Replace the dead qBittorrent exporter image pin with a live compatible image/tag and align the metrics port contract

## 2. Validation

- [ ] 2.1 Validate with `helm template haac-stack k8s/charts/haac-stack`
- [ ] 2.2 Publish the GitOps changes and verify `nvidia-device-plugin` stays healthy without a live-only patch
- [ ] 2.3 Verify `haac-gateway` is accepted and rerun `python scripts/haac.py wait-for-stack ...` until it either passes `haac-stack` or fails on a later concrete gate
