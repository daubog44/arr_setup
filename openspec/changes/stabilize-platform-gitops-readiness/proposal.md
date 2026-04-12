## Why

`task up` no longer fails in `configure-os`, but the GitOps readiness gate still stops almost immediately in `wait-for-stack`.

The concrete evidence is:

- `python scripts/haac.py wait-for-stack ...` fails on `haac-platform` because it remains `OutOfSync`
- the live `haac-platform` Application reports `Deployment.apps "argocd-repo-server" is invalid` during sync, which keeps the ArgoCD self-management path from converging
- the live `node-problem-detector` and `trivy-operator` Applications fail their first sync because they render `ServiceMonitor` objects before the monitoring CRDs are guaranteed to exist

That means `task up` still violates its contract after node configuration: platform GitOps is not deterministic yet.

## What Changes

- publish the ArgoCD install overlay as the stable source for the `argocd` Application instead of leaving the fix only in local untracked files
- keep the repo-server bootstrap patch in the install overlay and the imperative seed path aligned so ArgoCD self-management can converge instead of fighting invalid manifests
- order platform child Applications so monitoring CRDs land before Applications that render `ServiceMonitor`
- make the monitoring-dependent Applications tolerate first-sync missing CRDs during bootstrap

## Impact

- `wait-for-stack` can move past the `haac-platform` gate
- `task up` stops depending on a lucky timing window for ArgoCD self-management and monitoring CRD availability
- GitOps convergence becomes closer to the intended operator contract: rerunnable and phase-correct
