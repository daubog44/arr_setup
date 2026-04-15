## Why

`task up` still has two structural regressions after the previous cleanup:

1. the repo-local ArgoCD bootstrap overlay installs namespaced resources without a fixed namespace, so a fresh local bootstrap can create a second ArgoCD control plane in `default` before self-management converges in `argocd`;
2. Falco is now published as an official protected UI route, but the enabled chart profile still uses the legacy `ebpf` probe-build path and a persistent Redis-backed Web UI, which leaves the Application degraded on these unprivileged LXC nodes.

Both issues break the operator contract: the public UI surface reports Falco as official while the backing app is degraded, and the bootstrap path leaves cluster drift that is not repo-owned.

## What Changes

- make the repo-local ArgoCD install overlay namespace-safe from the first apply
- remove the legacy ArgoCD install left in `default` during bootstrap reconciliation
- switch Falco to an LXC-compatible `modern_ebpf` profile and remove the unnecessary persistent Redis requirement for the Web UI
- sync the accepted public-surface and archive-governance contracts into stable specs with real purposes

## Impact

- `task up` remains the same command, but ArgoCD bootstrap becomes single-owner from the first install
- Falco stays opt-in, but when enabled its official UI route is backed by a convergent chart profile
- stable OpenSpec specs stop carrying placeholder `TBD` purpose text
