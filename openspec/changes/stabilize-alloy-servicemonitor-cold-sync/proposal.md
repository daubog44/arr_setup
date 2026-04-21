## Why

The cold-cycle acceptance run for `.\haac.ps1 down` then `.\haac.ps1 up` failed in `GitOps readiness` even though the Cobra wrapper path worked. The first visible blocker was `alloy`, but live evidence shows the same failure shape also affects other platform child applications that emit `ServiceMonitor` or `PodMonitor` resources before Prometheus Operator CRDs are guaranteed to exist. Argo reports `one or more synchronization tasks are not valid` and leaves the app tree stalled on the first child gate it encounters.

## What Changes

- make `alloy` and other monitoring-CRD consumers recover cleanly when `ServiceMonitor` or `PodMonitor` CRDs appear later in the same cold bootstrap window
- improve child application ordering so `kube-prometheus-stack` lands before monitoring-CRD consumers
- validate the fix with the real `down` then `up` wrapper acceptance path

## Acceptance

- `alloy`, `crowdsec`, `kyverno`, and `policy-reporter` no longer strand the cold bootstrap on missing monitoring CRDs once Prometheus Operator is present
- `.\haac.ps1 up` succeeds after a destructive `.\haac.ps1 down`
