## Why

`task up` now reaches the later bootstrap phases, but the live control plane can still become unstable after platform reconciliation. The concrete evidence from the master `k3s` journal is:

- repeated timeouts on `127.0.0.1:6444`
- repeated slow Kine/SQLite queries
- repeated `scan-vulnerabilityreport-*` activity in the `security` namespace
- `metrics-server` becoming unavailable while the API server is already overloaded

The current `trivy-operator` Application is a strong suspect because it is configured broadly enough to scan the whole cluster, and the chart values in the repo currently place `targetNamespaces` under `operator`, which does not match the official chart shape. On a small single-master K3s control plane backed by SQLite/Kine, that is enough to create sustained job churn and destabilize the API.

## What Changes

- Correct the Trivy Operator chart values so namespace scoping uses the supported top-level keys.
- Reduce the default scan scope to workload namespaces and exclude platform/system namespaces from recurring scans.
- Lower scan concurrency and disable the more expensive scanners that are not worth their control-plane cost on this homelab by default.
- Push the Trivy Operator sync later in platform ordering so monitoring CRDs and core platform services settle first.
- Validate the result by rendering the manifest, validating the change, and rerunning the bootstrap path in the real environment.

## Capabilities

### New Capabilities

- `k3s-control-plane-load-safety`: Platform security scanning MUST not destabilize the single-master K3s control plane during or after `task up`.

## Impact

- `k8s/platform/applications/trivy-operator-app.yaml`
- `task up`
- master K3s API stability during platform and post-platform phases
