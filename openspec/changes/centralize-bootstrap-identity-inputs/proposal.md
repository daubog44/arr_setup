## Why

The current `.env.example` duplicates multiple service-specific usernames and passwords even though the bootstrap logic already partially derives several of them from a smaller core set:

- `QUI_PASSWORD` already fans out into qBittorrent and Homepage widget auth
- `AUTHELIA_ADMIN_PASSWORD` already fans out into Litmus defaults
- operators still need to set or understand separate values for ArgoCD, Semaphore, Grafana, Litmus, and Authelia without a clear default hierarchy

The user-facing requirement is to allow one main username/password to act as the default operator identity across the control-plane/admin stack while preserving explicit per-service overrides and keeping lower-trust downloader local auth explicit.

## What Changes

- Introduce a documented main identity/password layer in `.env.example`.
- Teach bootstrap code to derive service-specific defaults from that main identity where safe.
- Keep override variables supported for services that need a different local account or secret.
- Document which credentials are user-facing login defaults versus internal app secrets.

## Impact

- Operators can bootstrap the stack with fewer duplicated credential inputs.
- The credential model becomes clearer without removing per-service escape hatches.
- Downstream verification and secret generation stay deterministic when only the main identity is set.
