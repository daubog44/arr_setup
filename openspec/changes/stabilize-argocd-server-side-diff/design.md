## Design

### Evidence

- `python scripts/haac.py task-run -- wait-for-argocd-sync` showed `kyverno`, `kube-prometheus-stack`, and `litmus` as `OutOfSync` while healthy.
- `kubectl diff` returned exit code `0` for:
  - `deletingpolicies.policies.kyverno.io`
  - `kube-prometheus-stack-apiserver` `ServiceMonitor`
  - `litmus-mongodb` `StatefulSet`
- `kubectl apply --server-side --force-conflicts --dry-run=server -f ... -o json` produced zero semantic diffs for the same resources, which matches Argo CD's documented `ServerSideDiff` strategy.

### Solution shape

- Annotate the affected `Application` resources with `argocd.argoproj.io/compare-options: ServerSideDiff=true`.
- Keep `ServerSideApply=true` in sync options.
- Make the `kube-prometheus-stack` relabel action explicit so raw desired manifests do not rely on implicit defaults for the API server `ServiceMonitor`.
- Reconcile the affected applications after the manifest change and verify they move to `Synced`.

### Verification

- `openspec validate stabilize-argocd-server-side-diff`
- `& .\.tools\windows-amd64\bin\kubectl.exe kustomize k8s\platform`
- `python scripts/haac.py task-run -- wait-for-argocd-sync`
- live hard refresh or sync of the affected Argo CD applications
