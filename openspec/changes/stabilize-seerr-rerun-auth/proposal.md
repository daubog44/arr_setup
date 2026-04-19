## Why

`media:post-install` now reaches the Seerr settings phase, but reruns still fail because the Seerr Jellyfin auth payload is not idempotent. Live inspection on April 18, 2026 showed:

- `/api/v1/settings/public` reports `mediaServerType=2` and `jellyfinExternalHost` already populated
- `initialized=false`, so the setup is only partially complete
- the next `/api/v1/auth/jellyfin` call fails with `{"error":"Jellyfin hostname already configured"}`

The current bootstrap still always sends first-run server fields, even when Seerr already has Jellyfin configured.

## What Changes

- Make Seerr Jellyfin auth adaptive between first-run and rerun states.
- Send server connection fields only when Seerr has not yet configured a media server.
- Add focused regression coverage for first-run vs rerun auth payload selection.

## Capabilities

### New Capabilities

- `seerr-rerun-auth`: Define the idempotent Seerr Jellyfin auth contract across first-run and rerun states.

### Modified Capabilities

- `arr-stack-surface`: Media post-install must be rerunnable when Seerr is partially configured.

## Impact

- Affected code lives in [scripts/haac.py](C:/Users/Utente/OneDrive%20-%20ITS%20Tech%20Talent%20Factory/Desktop/dev/arr_setup-main/scripts/haac.py) and [tests/test_haac.py](C:/Users/Utente/OneDrive%20-%20ITS%20Tech%20Talent%20Factory/Desktop/dev/arr_setup-main/tests/test_haac.py).
- Verification must include OpenSpec validation, targeted Python unit tests, and a live `media:post-install` rerun that progresses beyond the Seerr rerun auth gate.
