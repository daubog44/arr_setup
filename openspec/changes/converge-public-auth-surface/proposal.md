## Why

The public UI surface already derives from one ingress catalog, but the live browser flows still diverge from the declared auth posture. Headlamp is declared as a protected management UI yet is not configured for a converged OIDC flow, while Homepage visibility and browser verification need to stay aligned with the same catalog instead of drifting at runtime.

## What Changes

- Converge the declared public auth matrix with the live browser behavior for official UIs.
- Enable and verify native Authelia OIDC where the repo already supports it cleanly, and keep edge forward-auth only for UIs that do not have a working native flow in this cluster.
- Add the missing cluster-side prerequisites for Headlamp native OIDC so the browser flow completes after Authelia login instead of falling back to the internal login page or an invalid request.
- Keep Homepage links, aliases, HTTPRoutes, and browser verification derived from the same ingress catalog so Litmus, ChaosTest, Falco, and the other published UIs stay visible when enabled.
- Require browser verification to use Playwright MCP when available and the repo-local Playwright CLI fallback when MCP is unavailable.

## Capabilities

### New Capabilities

- None.

### Modified Capabilities

- `public-ui-surface`: tighten the auth-strategy contract so the declared matrix matches the live browser-auth behavior, including Headlamp OIDC, Homepage alias visibility, and browser verification fallback rules.

## Impact

- `k8s/charts/haac-stack/config-templates/values.yaml.template`
- `k8s/charts/haac-stack/config-templates/configuration.yml.template`
- `k8s/charts/haac-stack/charts/mgmt/templates/headlamp.yaml`
- `k8s/charts/haac-stack/templates/httproutes.yaml`
- `scripts/verify-public-auth.mjs`
- `scripts/haac.py`
- `scripts/haaclib/endpoints.py`
- `ansible/playbook.yml`
- `openspec/specs/public-ui-surface/spec.md`
