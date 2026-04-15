## Design

### ArgoCD bootstrap

The install overlay must set `namespace: argocd` directly in the Kustomization, not rely on later self-management. This prevents a first `kubectl apply -k` from landing namespaced resources in `default`.

Because older runs already created a second control plane in `default`, `deploy_argocd` also performs a one-time cleanup of the known legacy ArgoCD resources from `default` after the repo-owned install in `argocd` is healthy.

### Falco on unprivileged LXC

The current Falco profile fails because it uses `driver.kind: ebpf`, which triggers build/mount behavior not supported in these guests. The chart supports `driver.kind: modern_ebpf`, which is the right profile for this environment. The Falcosidekick Web UI also does not need a persistent Redis PVC for this homelab; disabling Redis storage removes the failing Longhorn attach path while preserving the protected UI route.

### Spec cleanup

The two stable specs updated by the previous archive closeout need explicit `Purpose` text so the stable spec set is readable without reopening archived changes.
