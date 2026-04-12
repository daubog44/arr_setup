## Why

`task up` is already the intended one-command operator entrypoint, but today its success contract is still too implicit. The command provisions, configures, bootstraps GitOps, and verifies endpoints, yet it does not consistently expose phase boundaries, final public URLs, or failure points clearly enough for a homelab-as-code workflow.

## What Changes

- Define `task up` as a first-class bootstrap capability with explicit phase contracts.
- Require `task up` and the repo wrappers to emit a final, stable summary of visitable service URLs.
- Tighten the bootstrap contract around preflight checks, GitOps readiness gates, and endpoint verification output.
- Document what inputs from `.env` are required to run the full bootstrap path successfully.

## Capabilities

### New Capabilities
- `task-up-bootstrap`: A single-command bootstrap contract that provisions infrastructure, configures nodes, reconciles GitOps, publishes Cloudflare routing, and reports final public service URLs.

### Modified Capabilities
- None.

## Impact

- Affected operator entrypoints: `Taskfile.yml`, `haac.ps1`, `haac.sh`
- Affected orchestration logic: `scripts/haac.py`
- Affected generated configuration surfaces: `k8s/charts/haac-stack/values.yaml` and GitOps rendered manifests
- Affected operator documentation: `README.md`, `ARCHITECTURE.md`, runbooks
