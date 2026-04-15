# Why

The public UI surface is reachable again, but the auth contract is still inconsistent and that inconsistency is now the main correctness bug:

- Headlamp is configured for native OIDC in the deployment, but the registered Authelia redirect URI is wrong
- Semaphore is registered as an Authelia OIDC client, but the chart still renders it without native OIDC enabled
- official routes are still governed by the old boolean `auth_enabled`, which cannot express native OIDC, edge forward-auth, or app-native login without ambiguity
- some protected apps still risk a double-login path because the route-level middleware model does not distinguish edge auth from native auth
- Homepage, HTTPRoutes, and endpoint verification should all derive from one explicit auth strategy contract instead of inferring behavior from a boolean flag

## What Changes

- replace `auth_enabled` with an explicit `auth_strategy` in the ingress catalog
- define one supported public auth matrix for official UIs
- fix the Headlamp Authelia redirect URI mismatch and preserve native OIDC
- enable native OIDC for Semaphore with the correct Authelia provider redirect path
- keep edge forward-auth only for apps that do not have a mature native OIDC path in this repo
- keep Longhorn behind edge forward-auth until a repo-backed native auth path exists
- remove route-level forward-auth from native-OIDC and app-native routes to avoid double login
- suppress redundant local login affordances on control-plane apps where repo config supports it
- update endpoint verification so route auth posture is validated against the declared strategy
- sync the stable `public-ui-surface` capability spec to the new contract

## Expected Outcome

- Headlamp login completes without the current Authelia `invalid_request` failure
- Semaphore login completes through Authelia OIDC rather than through a second edge gate
- app-native routes present only the app's own login instead of an extra Authelia redirect
- edge-auth routes keep a single shared Authelia gate
- Homepage, HTTPRoutes, and URL verification remain derived from the same ingress catalog
