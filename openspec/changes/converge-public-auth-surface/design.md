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
- `edge_forward_auth`: Homepage, Headlamp, Ntfy, Litmus, Falco, Longhorn
- `native_oidc`: Semaphore, Grafana, ArgoCD
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

- do not keep native OIDC enabled in the deployment for the current in-cluster mode
- protect the UI with shared Authelia forward-auth and keep Headlamp on the standard in-cluster service-account path
- rationale: current upstream in-cluster OIDC flow reaches callback and issues a session cookie, but the main UI remains on `/c/main/login` with repeated unauthorized cluster requests, which does not satisfy the browser-verifiable auth contract

### Semaphore

- keep the provider-scoped Authelia redirect URI `/api/auth/oidc/authelia/redirect`
- browser verification must prove the route lands on the Semaphore UI with `login_with_password=false`
- repo config must not reintroduce a second edge gate for the route

### ArgoCD

- keep the built-in OIDC flow
- register the Authelia client with the token endpoint auth method that the deployed ArgoCD build actually uses
- remove duplicate legacy ArgoCD OIDC secret paths so one repo-managed secret contract remains
- keep each native-OIDC client on one plaintext secret source of truth inside the sealed Authelia config secret rather than a manual secret/hash pair in `.env`

## Verification

The change is only done when:

- OpenSpec validates
- Helm and Kustomize renders pass
- `task -n up` passes
- `verify-web` reflects the declared auth strategies
- browser checks confirm:
  - Headlamp presents one Authelia edge gate and no second broken internal login path
  - ArgoCD native OIDC completes without the current token endpoint auth-method mismatch
  - Semaphore native OIDC completes
  - Homepage, Litmus, and Falco show one Authelia gate
  - app-native routes do not get an Authelia redirect
