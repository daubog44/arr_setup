## Why

The repo now boots reliably enough to reach the public URL phase, but the operator-facing surface is still inconsistent. The official route catalog excludes Falco and Litmus, Homepage no longer shows those UIs, some routes are still public while others are protected, and several old bootstrap changes remain active even though the accepted behavior already lives in stable specs or in the mainline code.

## What Changes

- Add a single declarative public UI catalog that covers all official browser-facing apps, including Falco and Litmus, and use it for HTTPRoutes, Homepage links, and endpoint verification.
- Make Authelia forward-auth the default protection model for published app UIs, with explicit opt-out only where the route must stay public.
- Add first-class route metadata for enabled/disabled publication so opt-in platform apps such as Falco do not create dead Homepage links or false verification failures.
- Clean up the stale bootstrap change backlog by syncing accepted requirements into stable specs and archiving superseded in-progress changes.
- Revalidate the official public surface end to end and republish the GitOps state.

## Capabilities

### New Capabilities
- `public-ui-surface`: Defines the official published UI catalog, its auth posture, Homepage visibility, and endpoint verification contract.

### Modified Capabilities
- `task-up-bootstrap`: Tighten the public URL contract so the final emitted URLs come from the official UI catalog and reflect the real auth posture.
- `openspec-change-archival`: Require stale or superseded bootstrap changes to be archived once their accepted requirements have been synced into stable specs.

## Impact

- `k8s/charts/haac-stack/config-templates/values.yaml.template`
- `k8s/charts/haac-stack/values.yaml`
- `k8s/charts/haac-stack/templates/homepage-config.yaml`
- `k8s/charts/haac-stack/templates/httproutes.yaml`
- `k8s/charts/haac-stack/templates/auth-middlewares.yaml`
- `scripts/haac.py`
- `scripts/haaclib/endpoints.py`
- `README.md`
- `ARCHITECTURE.md`
- `openspec/specs/*`
- `openspec/changes/*`
