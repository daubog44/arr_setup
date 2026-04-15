# Design

## ArgoCD bootstrap

The repo already vendors the initial ArgoCD manifests. The fix is to make that bootstrap overlay explicitly namespace-scoped and to add one cleanup pass for legacy `argocd-*` resources previously created in `default`.

The cleanup is bounded:

- namespace-scoped only
- only `argocd-*` names
- executed during `deploy-argocd`

## Falco

The current LXC environment cannot sustain the legacy `ebpf` probe build path. The Falco chart already supports `modern_ebpf`, which avoids the failing driver-loader build path.

The Falcosidekick UI should not depend on a Redis PVC in this homelab. Disabling UI Redis persistence makes the UI stateless and avoids Longhorn readiness blocking the official route.

Because the route is already protected by Authelia forward-auth, the UI's own basic auth can be disabled.

## Verification

- `helm template` renders the Falco app values cleanly
- `task reconcile:argocd` removes the legacy default-namespace ArgoCD resources
- `task verify-cluster` shows only the intended ArgoCD install and healthy route backends
- `task verify-endpoints` reports Homepage, Semaphore, Litmus, and Falco as protected reachable URLs
