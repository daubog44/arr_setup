## Why

`litmus.nucleoautogenerativo.it` is still declared as `edge_forward_auth`, but the deployed Litmus chart keeps its own internal username/password login and does not expose a repo-managed native OIDC integration. The current browser flow therefore lands on a second login screen after Authelia, which violates the repo policy for unsupported native OIDC apps.

The public UI contract is also inconsistent: Homepage still renders the `ChaosTest` alias from the same Litmus route, so the same UI appears twice even though the operator now wants one canonical `Litmus` entry.

## What Changes

- Change Litmus from `edge_forward_auth` to `app_native` in the public ingress catalog.
- Remove the `ChaosTest` Homepage alias from the Litmus route definition.
- Introduce a repo-managed Litmus admin secret derived from operator inputs instead of relying on the chart default `admin/litmus`.
- Update browser verification so Litmus is only considered healthy if the app-native login succeeds with the repo-managed admin credential.
- Update the stable public UI spec so Litmus is modeled as one canonical app-native route.

## Impact

- Litmus will no longer sit behind the shared Authelia forward-auth middleware.
- The operator gets a single Homepage entry for Litmus.
- The Litmus login becomes explicit, deterministic, and repo-managed instead of chart-default.
