## Design

The issue is an ArgoCD cold-bootstrap ordering blind spot, not an Alloy chart bug.

During a destructive cluster rebuild, the `alloy` application can be created before the `ServiceMonitor` CRD from `kube-prometheus-stack` is available. ArgoCD rejects the sync task graph before the CRD settles, which stalls `task up` in `GitOps readiness`.

The minimal safe fix is to add `SkipDryRunOnMissingResource=true` to the `alloy` application sync options. This matches the repo's existing pattern for apps that depend on CRDs created elsewhere during the same cold bootstrap window.

Validation must use the real Cobra-supported wrapper path after a cold cycle, not only dry renders.
