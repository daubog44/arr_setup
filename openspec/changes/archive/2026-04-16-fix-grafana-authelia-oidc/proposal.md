## Why

Grafana native OIDC is currently broken against Authelia: the browser reaches Grafana, but token exchange fails and the login page renders `Failed to get token from provider`. This must be fixed now because `native_oidc` is part of the stable public UI contract and the current browser verification is too weak to catch this class of failure.

## What Changes

- Fix the Grafana OIDC client-secret wiring so the deployed Grafana container receives the client secret under the environment variable name it actually reads.
- Tighten browser verification so Grafana native OIDC only passes when the flow reaches an authenticated Grafana landing page, not when the login page renders with an OAuth error.
- Reconcile the affected GitOps artifacts and validate the live browser flow after deployment.

## Capabilities

### New Capabilities

- None.

### Modified Capabilities

- `public-ui-surface`: Native OIDC verification and secret-wiring requirements now explicitly cover application-expected client-secret exposure and browser-level failure detection.

## Impact

- Affected code: `scripts/haac.py`, `scripts/verify-public-auth.mjs`, and the rendered Grafana OIDC Sealed Secret.
- Affected systems: Authelia OIDC, Grafana native OIDC login, and final browser-level public UI verification.
