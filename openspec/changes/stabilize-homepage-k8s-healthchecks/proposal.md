## Why

The public Homepage route currently fails browser verification because the service loses ready endpoints even though the container process starts. The repo-managed Deployment only allows the public host in `HOMEPAGE_ALLOWED_HOSTS` and probes `/`, while Homepage's official Kubernetes guidance requires the pod IP in the allow-list and probes against `/api/healthcheck`. That mismatch can cause kubelet health checks to hit host validation instead of a stable internal health endpoint, leaving the service effectively unavailable.

## What Changes

- Align the Homepage Deployment with the upstream Kubernetes health contract.
- Add the pod IP to `HOMEPAGE_ALLOWED_HOSTS` while preserving the public domain host.
- Move liveness and readiness probes to Homepage's healthcheck endpoint.
- Re-validate the public Homepage route through the existing browser verification path.

## Impact

- Homepage should remain ready behind Kubernetes probes instead of flapping between `Running` and unready.
- Public URL verification regains a stable management landing page, unblocking the end-to-end browser gate.
