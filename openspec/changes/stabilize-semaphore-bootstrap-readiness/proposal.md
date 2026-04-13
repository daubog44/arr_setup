## Why

`task up` now reaches the GitOps readiness phase, but it still fails because `haac-stack` waits on `semaphore-bootstrap`. Live cluster evidence shows the Semaphore Application is rendered with values that do not match the official chart schema for version `16.0.11`, so the workload runs with the chart defaults while the bootstrap Job still assumes the old local admin and database contract.

## What Changes

- Align `k8s/platform/applications/semaphore-app.yaml.template` with the official Semaphore chart schema used by `targetRevision: 16.0.11`.
- Make the public Semaphore route use the existing Authelia/Traefik middleware chain instead of relying on the chart's unsupported OIDC secret-ref shape.
- Extend the generated Semaphore sealed secret contract so the chart can create the local admin user declaratively without embedding raw secrets in tracked manifests.
- Convert `semaphore-bootstrap` from a Helm hook into a rerunnable Argo-managed Job and keep its API bootstrap path idempotent.
- Validate the change by publishing the GitOps revision and rerunning the `haac-stack` readiness gate until it either passes `semaphore-bootstrap` or fails on a later concrete blocker.

## Capabilities

### New Capabilities
- `semaphore-bootstrap-readiness`: Semaphore chart values, secrets, and bootstrap resources converge declaratively and stop blocking `task up`.

### Modified Capabilities
- `task-up-bootstrap`: The GitOps readiness phase now requires the Semaphore bootstrap branch to converge with a chart-compatible, rerunnable contract.

## Impact

- `k8s/platform/applications/semaphore-app.yaml.template`
- `k8s/platform/applications/semaphore-app.yaml`
- `k8s/charts/haac-stack/charts/mgmt/templates/semaphore-bootstrap.yaml`
- `k8s/charts/haac-stack/templates/secrets/semaphore-sealed-secret.yaml`
- `scripts/haac.py`
- `openspec/specs/task-up-bootstrap/spec.md`
