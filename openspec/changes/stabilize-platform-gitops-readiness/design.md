## Design

### ArgoCD self-management

The `argocd` child Application should point at a repo-local install overlay that wraps the upstream ArgoCD `cluster-install` manifest and applies the repo-server patch through Kustomize. The same patch path is already used by the imperative bootstrap seed in `scripts/haac.py`, so the declarative and imperative flows must share the same file.

### Monitoring CRD ordering

`kube-prometheus-stack` is the platform producer of `ServiceMonitor` CRDs. Child Applications that render `ServiceMonitor` on their first sync must not run in the same readiness lane without ordering. The fix is:

- give `kube-prometheus-stack` an earlier sync wave
- give `node-problem-detector` and `trivy-operator` a later sync wave
- add `SkipDryRunOnMissingResource=true` to those dependent Applications so bootstrap does not fail on a transient first-sync missing CRD

### Validation

Validation needs both local render proof and live cluster proof:

- local `kubectl kustomize` of the ArgoCD install overlay must emit a valid merged `argocd-repo-server` Deployment
- live `wait-for-stack` must move past `haac-platform`
- the remaining blocker, if any, should then be a later platform or workload issue rather than the current platform sync deadlock
