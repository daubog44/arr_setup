# Why

Two structural defects still sit in the `task up` path:

- the repo-local ArgoCD bootstrap can leave a legacy install in `default` while the intended install lives in `argocd`
- Falco is part of the official public UI catalog, but the current runtime profile is still not coherent with unprivileged Proxmox LXC guests

That leaves the cluster with avoidable drift and a degraded official route.

## What Changes

- harden the repo-local ArgoCD bootstrap so it converges on one namespaced install only
- remove legacy `argocd-*` resources left in `default`
- switch Falco to the chart-supported `modern_ebpf` profile for this environment
- make the Falcosidekick UI stateless and rely on Authelia protection instead of its own built-in basic auth
- align stable OpenSpec archival/spec wording with the actual archived state

## Expected Outcome

- `task reconcile:argocd` and `task up` no longer leave a duplicate ArgoCD install in `default`
- `falco.nucleoautogenerativo.it` remains an official protected UI route and the platform app converges much closer to healthy
- stable OpenSpec docs stop carrying placeholder archive text
