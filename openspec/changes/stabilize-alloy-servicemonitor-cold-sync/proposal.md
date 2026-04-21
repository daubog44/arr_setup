## Why

The cold-cycle acceptance run for `.\haac.ps1 down` then `.\haac.ps1 up` failed in `GitOps readiness` even though the Cobra wrapper path worked. The live blocker was the `alloy` ArgoCD application: it rendered a `ServiceMonitor` before the Prometheus Operator CRD surface was guaranteed to exist, and Argo reported `one or more synchronization tasks are not valid`.

## What Changes

- make the `alloy` ArgoCD application tolerate missing `ServiceMonitor` CRDs during cold bootstrap
- validate the fix with the real `down` then `up` wrapper acceptance path

## Acceptance

- `alloy` no longer fails cold sync planning on `ServiceMonitor/alloy`
- `.\haac.ps1 up` succeeds after a destructive `.\haac.ps1 down`
