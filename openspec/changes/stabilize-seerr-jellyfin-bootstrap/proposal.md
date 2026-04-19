## Why

After the downloader and ARR service-probe fixes, `media:post-install` now reaches the Seerr bootstrap stage and fails on April 18, 2026 with:

```text
Seerr could not authenticate against Jellyfin with the effective Jellyfin admin credentials.
HTTP 500
{"error":"No hostname provided."}
```

Live evidence shows the failure is not a bad Jellyfin password. The repo-managed bootstrap currently posts only `username`, `password`, and `email` to Seerr, while the Seerr API and setup flow require additional Jellyfin connection fields such as `hostname`, `port`, `useSsl`, and `serverType`.

## What Changes

- Stabilize the Seerr Jellyfin login bootstrap so it uses the actual API contract expected by Seerr.
- Keep the post-install path opinionated toward the repo-managed in-cluster Jellyfin service while still publishing the external hostname into Seerr settings afterward.
- Add focused regression coverage so future Seerr upgrades do not silently regress the setup payload.

## Capabilities

### New Capabilities

- `seerr-jellyfin-bootstrap`: Define the supported API contract for bootstrapping Seerr against the repo-managed Jellyfin service.

### Modified Capabilities

- `arr-stack-surface`: Media post-install must be able to initialize Seerr against Jellyfin without manual UI setup when the repo-managed media services are healthy.

## Impact

- Affected code lives in [scripts/haac.py](C:/Users/Utente/OneDrive%20-%20ITS%20Tech%20Talent%20Factory/Desktop/dev/arr_setup-main/scripts/haac.py) and [tests/test_haac.py](C:/Users/Utente/OneDrive%20-%20ITS%20Tech%20Talent%20Factory/Desktop/dev/arr_setup-main/tests/test_haac.py).
- Verification must include OpenSpec validation, targeted Python unit tests, and a live `media:post-install` rerun that reaches beyond the Seerr Jellyfin authentication step.
