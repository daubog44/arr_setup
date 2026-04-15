# Design

## ArgoCD bootstrap

The repo already vendors the initial ArgoCD manifests and the current source already converges on `argocd`. The remaining work is to keep the legacy cleanup bounded and to stop the active change text from describing a duplicate-bootstrap problem that no longer exists in source.

The cleanup is bounded:

- namespace-scoped only
- only `argocd-*` names
- executed during `deploy-argocd`

## Falco

The current LXC environment cannot sustain a reliable Falco runtime syscall probe by default. `modern_ebpf` avoids the old driver-loader build path, but unprivileged Proxmox LXC guests still cannot host the runtime sensor unless an operator explicitly labels a compatible node.

The Falcosidekick UI should not depend on a Redis PVC in this homelab. Disabling UI Redis persistence makes the UI stateless and avoids Longhorn readiness blocking the official route.

Because the route is already protected by Authelia forward-auth, the UI's own basic auth can be disabled.

The robust default is:

- keep the Falco public route and Homepage entry
- keep the Falcosidekick UI plus Redis ephemeral and reconcile-safe
- require an explicit compatible-node label before the runtime DaemonSet schedules anywhere
- treat runtime sensor enablement as a separate host-compatibility decision, not a default bootstrap assumption

## Verification

- `helm template` renders the Falco app values cleanly
- `task reconcile:argocd` removes the legacy default-namespace ArgoCD resources
- `task verify-cluster` shows only the intended ArgoCD install and healthy route backends
- `task verify-endpoints` reports Homepage, Semaphore, Litmus, and Falco as protected reachable URLs
