## Overview

This change converges the official public UI catalog with the actual browser login flows. The ingress catalog already carries `auth_strategy`, so the work is not to invent another abstraction. The work is to make the declared strategy true at runtime, especially for Headlamp, and to make browser verification fail when a route only looks healthy at the HTTP layer.

## Current State

- `values.yaml.template` already declares `auth_strategy` per official route.
- `HTTPRoute` rendering already adds the Authelia middleware only to `edge_forward_auth` routes.
- Semaphore, Grafana, and ArgoCD already have native OIDC config.
- Headlamp is still deployed only with `-in-cluster`, so the route cannot satisfy a native OIDC contract today.
- Homepage links and aliases already derive from the same ingress catalog, including the `ChaosTest` alias under `litmus`.
- `verify-public-auth.mjs` already performs browser verification, but it still treats Headlamp as an edge-auth route rather than a real native OIDC route.

## Design Decisions

### 1. Keep the existing ingress catalog as the only route source of truth

No new route catalog is introduced. The existing `ingresses` map remains the source for:

- HTTPRoutes
- Homepage links and aliases
- endpoint verification
- auth expectation reporting

This avoids a second control plane for route metadata.

### 2. Keep Headlamp on a single-login edge-auth path until upstream OIDC is trustworthy

Headlamp's official documentation supports OIDC, but the current Headlamp plus Authelia browser flow for this repo reproduces an upstream failure mode: the popup completes Authelia login and consent, then the main page returns to the local `Use A Token` screen instead of converging to the dashboard. The same failure signature is tracked upstream in the Headlamp project.

So the robust choice for this repo is:

- keep `headlamp` on `edge_forward_auth`
- keep the single shared Authelia gate at the edge
- mount a repo-managed in-cluster kubeconfig into Headlamp so the UI lands directly on the cluster instead of prompting for a second token

Implementation shape:

- remove the attempted native OIDC route declaration for Headlamp
- create a dedicated Headlamp service account and static kubeconfig config map
- mount that kubeconfig at the location Headlamp already probes on startup
- bind that service account to the cluster access level chosen by the repo

This is not a shortcut. It is a product-level fallback chosen from evidence, and it is aligned with Headlamp's documented shared-deployment model.

### 3. Preserve single-login behavior per route

The route matrix after this change is:

- `public`: Authelia
- `native_oidc`: Semaphore, Grafana, ArgoCD
- `edge_forward_auth`: Homepage, Ntfy, Litmus, Falco, Longhorn
- `edge_forward_auth`: Headlamp
- `app_native`: Jellyfin, Radarr, Sonarr, Prowlarr, Autobrr, qBittorrent/QUI

Longhorn intentionally remains `edge_forward_auth` because the repo does not provide a first-party native login flow for it. The change is about converged and truthful auth behavior, not forcing every route into OIDC regardless of product support.

### 4. Browser verification becomes the acceptance gate for native OIDC routes

HTTP reachability is not enough for `native_oidc`. Browser verification must prove:

- the app lands on the expected host after Authelia login
- the expected post-login UI appears
- the app does not fall back to an internal login screen or an invalid callback flow

Verification policy:

- prefer Playwright MCP when available
- if MCP is unavailable, use the repo-local Playwright CLI/browser script path

### 5. Homepage visibility is validated from the rendered catalog, not by ad hoc UI assumptions

This change does not add separate Homepage entries for Litmus and ChaosTest by hand. Instead:

- keep `homepage_aliases` under `litmus`
- ensure the rendered Homepage config still includes both entries
- ensure runtime deployment rolls when the catalog changes

## Implementation Plan

1. Update OpenSpec delta spec for `public-ui-surface`.
2. Remove stale Headlamp OIDC client and secret rendering from the repo-managed Authelia configuration.
3. Update Headlamp deployment to use the shared in-cluster kubeconfig fallback with a repo-managed, non-admin default Kubernetes access level.
4. Tighten browser verification for Headlamp and the overall route matrix.
5. Reconcile the cluster, verify live routes, and archive the change if review passes.

## Risks And Mitigations

### Risk: Shared Headlamp kubeconfig creates a broader cluster credential than per-user OIDC would

Mitigation:

- keep Headlamp behind the shared Authelia edge gate
- keep this fallback explicit in the route contract
- keep the mounted Kubernetes credential on a repo-managed, non-admin default role
- revisit native OIDC only when the upstream browser flow is proven stable in this repo

### Risk: Homepage links are correct in source but stale in runtime

Mitigation:

- reconcile ArgoCD after the change
- check rendered Homepage config and browser-visible entries
