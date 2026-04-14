## Design

### Root cause shape

The live evidence points to control-plane overload rather than a hard K3s crash:

- `k3s server` remains running and bound to `6443`
- the API server times out on discovery and object listing
- Kine/SQLite logs slow SQL while Trivy scan jobs in `security` keep churning

This is consistent with too much report-generation pressure on a single-master SQLite-backed cluster.

### Trivy Operator changes

The Trivy Operator chart supports:

- top-level `targetNamespaces`
- top-level `excludeNamespaces`
- `operator.scanJobsConcurrentLimit`
- per-scanner enable/disable flags under `operator`

The repo currently nests `targetNamespaces` under `operator`, so the intended scope reduction is not actually applied. The fix is:

- move `targetNamespaces` to the top level
- target only workload namespaces by default
- exclude system/platform namespaces explicitly
- set `scanJobsConcurrentLimit` to `1`
- keep vulnerability scanning enabled
- disable `sbom`, `config audit`, `RBAC assessment`, `infra assessment`, `cluster compliance`, and `exposed secret` scanning by default on this stack
- keep `serviceMonitor.enabled=true`

This preserves a useful default security signal without allowing Trivy to dominate the control plane.

### Ordering

`trivy-operator` should not be one of the earliest platform apps. It is not required for bootstrap correctness. Moving it later reduces contention during the critical stabilization window.

## Validation

- `openspec validate stabilize-k3s-control-plane-load`
- `helm template haac-stack k8s/charts/haac-stack`
- `kubectl kustomize k8s/platform`
- `python scripts/haac.py task-run -- -n up`
- live `task up` when the environment is available

The live success condition is not only that `task up` finishes. The control plane must stay responsive enough that later phases can still query the API.
