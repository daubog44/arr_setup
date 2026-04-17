## 1. Manifest updates

- [x] 1.1 Enable Argo CD server-side diff on the affected repo-managed applications that still show false `OutOfSync`
- [x] 1.2 Make compare-relevant implicit defaults explicit where the repo can do so safely
- [x] 1.3 Add or update the stable GitOps compare capability spec

## 2. Verification

- [ ] 2.1 Validate with OpenSpec, `kubectl kustomize`, and a live Argo CD reconcile/refresh showing the affected apps as `Synced`
