## Why

`task up` no longer fails in `configure-os`, but the GitOps readiness gate still stops almost immediately in `wait-for-stack`.

The concrete evidence is:

- `python scripts/haac.py wait-for-stack ...` fails on `haac-platform` because it remains `OutOfSync`
- the live `haac-platform` Application reports `Deployment.apps "argocd-repo-server" is invalid` during sync, which keeps the ArgoCD self-management path from converging
- the live `node-problem-detector` and `trivy-operator` Applications fail their first sync because they render `ServiceMonitor` objects before the monitoring CRDs are guaranteed to exist
- after publishing the repo-local overlay, the live `argocd` Application can still fall back to `sync=Unknown` because manifest generation depends on a remote Kustomize Git fetch that times out inside ArgoCD
- after the self-managed ArgoCD upgrade, the new `argocd-dex-server` pod can fail with `CreateContainerConfigError` because the Dex image now exposes a non-numeric user and the upstream manifest only sets `runAsNonRoot`

That means `task up` still violates its contract after node configuration: platform GitOps is not deterministic yet.

## What Changes

- publish the ArgoCD install overlay as the stable source for the `argocd` Application instead of leaving the fix only in local untracked files
- vendor the pinned upstream ArgoCD install manifests into the repo so the self-managed `argocd` Application does not rely on runtime network fetches during manifest generation
- keep the repo-server bootstrap patch in the install overlay and the imperative seed path aligned so ArgoCD self-management can converge instead of fighting invalid manifests
- patch the self-managed Dex deployment with an explicit numeric UID/GID so ArgoCD can complete the upgrade without leaving the app degraded
- order platform child Applications so monitoring CRDs land before Applications that render `ServiceMonitor`
- make the monitoring-dependent Applications tolerate first-sync missing CRDs during bootstrap

## Impact

- `wait-for-stack` can move past the `haac-platform` gate
- `task up` stops depending on a lucky timing window for ArgoCD self-management and monitoring CRD availability
- ArgoCD self-management stops depending on a remote Git fetch inside manifest generation
- GitOps convergence becomes closer to the intended operator contract: rerunnable and phase-correct
