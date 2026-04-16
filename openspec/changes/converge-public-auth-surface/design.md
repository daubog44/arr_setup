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

### 2. Converge Headlamp to real native OIDC instead of keeping a misleading edge-auth declaration

Headlamp's official documentation requires:

- a client ID
- a client secret
- an issuer URL
- a callback URL at `/oidc-callback`

Headlamp native OIDC also requires the Kubernetes API server to accept the tokens that Headlamp presents after the browser login. This repo does not currently configure K3s API-server OIDC, so Headlamp cannot be treated as native OIDC without adding that cluster-side prerequisite.

Implementation shape:

- add an Authelia OIDC client for `headlamp`
- generate a sealed secret for the Headlamp OIDC client secret
- configure Headlamp with OIDC env vars and keep `-in-cluster`
- configure K3s server OIDC flags for the same issuer and client ID
- bind the `admins` group to the Headlamp-required cluster access level

The cluster OIDC contract is intentionally limited to this repo's Headlamp flow. It does not attempt to redesign workstation `kubectl` auth in the same change.

### 3. Preserve single-login behavior per route

The route matrix after this change is:

- `public`: Authelia
- `native_oidc`: Headlamp, Semaphore, Grafana, ArgoCD
- `edge_forward_auth`: Homepage, Ntfy, Litmus, Falco, Longhorn
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
2. Add Headlamp OIDC client generation and secret rendering.
3. Configure K3s API-server OIDC flags and RBAC for the `admins` group.
4. Update Headlamp deployment to use native OIDC.
5. Tighten browser verification for Headlamp and the overall route matrix.
6. Reconcile the cluster, verify live routes, and archive the change if review passes.

## Risks And Mitigations

### Risk: K3s API server OIDC breaks cluster access

Mitigation:

- add only additive OIDC flags
- keep the existing service-account-based Headlamp deployment shape
- validate `task -n up` and live `task up`

### Risk: Headlamp callback still mismatches because of reverse-proxy headers

Mitigation:

- keep the shared `force-https` middleware
- browser-verify the real callback URL

### Risk: Homepage links are correct in source but stale in runtime

Mitigation:

- reconcile ArgoCD after the change
- check rendered Homepage config and browser-visible entries
