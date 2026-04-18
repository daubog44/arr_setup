## 1. Recyclarr bootstrap

- [ ] 1.1 Add a repo-managed Recyclarr config template for the supported Sonarr and Radarr defaults
- [ ] 1.2 Add bootstrap helpers that generate the runtime Recyclarr Secret from the live ARR API keys
- [ ] 1.3 Run Recyclarr sync during `media:post-install` and keep the CronJob as the steady-state reconciler

## 2. Verification

- [ ] 2.1 Add focused regression coverage for Recyclarr config rendering/bootstrap
- [ ] 2.2 Validate with OpenSpec, targeted unit tests, Helm render, and a live `task media:post-install` rerun
