## 1. Revision freshness

- [x] 1.1 Refresh the repo-managed ArgoCD root application after bootstrap apply and require repo-managed readiness gates to match the expected GitOps commit, including stale failed/degraded revisions
- [x] 1.2 Add focused regression coverage for stale-but-healthy ArgoCD applications
- [x] 1.3 Record the revision freshness contract in OpenSpec

## 2. Validation

- [x] 2.1 Validate with OpenSpec, targeted tests, dry-run bootstrap, live reconcile, and browser checks when the cluster is reachable
