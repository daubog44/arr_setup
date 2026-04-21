## Design

The issue is an ArgoCD cold-bootstrap ordering blind spot across the monitoring surface, not an Alloy-specific chart bug.

During a destructive cluster rebuild, `alloy`, `crowdsec`, `kyverno`, and `policy-reporter` can begin syncing before the `ServiceMonitor` and `PodMonitor` CRDs from `kube-prometheus-stack` exist. ArgoCD rejects the sync task graph before those CRDs settle, which stalls `task up` in `GitOps readiness`.

The fix has two layers:

1. declarative ordering:
   - move `kube-prometheus-stack` earlier in the platform application waves
   - keep monitoring-CRD consumers after it
   - add `SkipDryRunOnMissingResource=true` where the child app can still race the CRD surface

2. runtime recovery:
   - broaden the existing ArgoCD recovery helper so `wait-for-stack` recognizes both `ServiceMonitor` and `PodMonitor` cold-sync failures
   - once the required CRD exists, force a hard refresh and re-sync of the affected child application instead of failing the whole bootstrap

Validation must use the real Cobra-supported wrapper path after a cold cycle, not only dry renders.
