# Design

## Scope

This change owns the public UI auth contract and route behavior. It does not yet redesign the Semaphore infrastructure SSH trust model or Cloudflare publication rules; those belong to later changes.

## Auth strategy model

The ingress catalog gains one required field:

- `auth_strategy`

Allowed values:

- `public`
- `edge_forward_auth`
- `native_oidc`
- `app_native`

The declared strategy becomes the single route-auth source of truth for:

- rendered HTTPRoute middleware chains
- generated Homepage metadata
- operator-facing endpoint verification

## Auth matrix

- `public`: Authelia only
- `edge_forward_auth`: Homepage, Ntfy, Litmus, Falco, Longhorn
- `native_oidc`: Headlamp, Semaphore, Grafana, ArgoCD
- `app_native`: Jellyfin, Radarr, Sonarr, Prowlarr, Autobrr, qBittorrent/QUI

## Route behavior

### edge_forward_auth

Routes keep the Traefik `authelia` middleware and are considered successful when they redirect or challenge through Authelia.

### native_oidc

Routes must not receive the Traefik `authelia` middleware. Browser verification must prove that the app's own OIDC login flow completes after the Authelia identity step.
Where the upstream application supports it, repo-side config must suppress the redundant local login UI.

### app_native

Routes must not receive the Traefik `authelia` middleware. HTTP verification only checks availability; browser verification must confirm the app presents its own login, not an Authelia redirect.

### public

Routes are expected to answer directly without authentication middleware.

## Specific app fixes

### Headlamp

- keep native OIDC in the deployment
- update the Authelia client redirect URI from `/oidc/callback` to `/oidc-callback`
- reduce the in-cluster RBAC blast radius from `cluster-admin` to a read-only cluster role suitable for the dashboard

### Semaphore

- enable native OIDC in the Helm application values
- use the provider-scoped Authelia redirect URI `/api/auth/oidc/authelia/redirect`

## Verification

The change is only done when:

- OpenSpec validates
- Helm and Kustomize renders pass
- `task -n up` passes
- `verify-web` reflects the declared auth strategies
- browser checks confirm:
  - Headlamp native OIDC completes without the current redirect mismatch
  - Semaphore native OIDC completes
  - Homepage, Litmus, and Falco show one Authelia gate
  - app-native routes do not get an Authelia redirect
