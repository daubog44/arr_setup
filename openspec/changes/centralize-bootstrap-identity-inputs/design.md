## Context

Today the repo mixes three different classes of inputs in `.env`:

1. human login credentials
2. service-local bootstrap admin credentials
3. opaque application secrets such as OIDC client secrets, cookie keys, and DB passwords

The first class is a good candidate for a main identity/password default. The second class can often derive from it, but not always. The third class must remain separate and random.

## Goals

- Add a single default operator identity/password layer for login-oriented surfaces.
- Preserve service-specific overrides.
- Avoid deriving opaque machine secrets from the main password.
- Keep bootstrap, secret generation, and browser verification consistent.

## Non-Goals

- Replacing OIDC client secrets, DB passwords, or encryption keys with the main password.
- Removing service-specific overrides.
- Forcing services with fixed or awkward bootstrap usernames to pretend they support arbitrary usernames if they do not.

## Design

1. Add new env inputs:
   - `HAAC_MAIN_USERNAME`
   - `HAAC_MAIN_PASSWORD`
   - `HAAC_MAIN_EMAIL`
   - `HAAC_MAIN_NAME`

2. In `merged_env()`, derive login-oriented defaults when a service-specific value is absent:
   - `AUTHELIA_ADMIN_USERNAME/PASSWORD`
   - `ARGOCD_USERNAME/PASSWORD`
   - `SEMAPHORE_ADMIN_USERNAME/PASSWORD/EMAIL/NAME`
   - `LITMUS_ADMIN_USERNAME/PASSWORD`
   - `GRAFANA_ADMIN_USERNAME/PASSWORD`
   - Keep `QBITTORRENT_USERNAME` and `QUI_PASSWORD` explicit so the downloader local auth does not silently inherit the control-plane password.

3. Keep opaque secrets independent:
   - `SEMAPHORE_DB_PASSWORD`
   - `SEMAPHORE_APP_SECRET`
   - `SEMAPHORE_COOKIE_HASH`
   - `SEMAPHORE_COOKIE_ENCRYPTION`
   - `ARGOCD_OIDC_SECRET`
   - `SEMAPHORE_OIDC_SECRET`
   - `GRAFANA_OIDC_SECRET`
   - `AUTHELIA_SESSION_SECRET`
   - `AUTHELIA_STORAGE_ENCRYPTION_KEY`
   - `AUTHELIA_JWT_SECRET`

4. Update Authelia user hydration and supporting templates so the local Authelia admin identity can derive from the main identity instead of being hardcoded to `admin`.

5. Update Homepage widget secret generation, Grafana admin secret generation, and browser verification so they follow the same derived defaults without collapsing the downloader local auth onto the main admin password.

6. Rewrite `.env.example` comments so operators can tell:
   - what can be left to the main identity defaults
   - what is an explicit override
   - what must stay unique/random

## Risks

- Changing bootstrap usernames for some apps can break login expectations if the service or verification logic still assumes `admin`.
  - Mitigation: update generation and verification code in the same change.
- Over-centralizing secrets can weaken separation of duties.
  - Mitigation: only derive human login credentials; keep machine secrets separate.
