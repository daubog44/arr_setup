# Why

Two structural defects still sit in the `task up` path:

- the repo-local ArgoCD bootstrap/spec wording is stale even though the source already converges on a single install in `argocd`
- Falco is part of the official public UI catalog, but the current runtime/UI profile is still not coherent with unprivileged Proxmox LXC guests

That leaves the cluster with avoidable drift and a degraded official route.

## What Changes

- align the repo-local ArgoCD bootstrap wording with the already-correct namespaced install
- keep the legacy `argocd-*` cleanup bounded to `default`
- keep the Falco public route healthy under Authelia while making runtime sensor scheduling explicit opt-in on compatible nodes
- make the Falcosidekick UI stateless and rely on Authelia protection instead of its own built-in basic auth
- align stable OpenSpec archival/spec wording with the actual archived state

## Expected Outcome

- `task reconcile:argocd` and `task up` converge on a single namespaced ArgoCD install in `argocd`
- `falco.nucleoautogenerativo.it` remains an official protected UI route and the platform app converges to a healthy UI surface under unprivileged-LXC defaults
- stable OpenSpec docs stop carrying placeholder archive text
