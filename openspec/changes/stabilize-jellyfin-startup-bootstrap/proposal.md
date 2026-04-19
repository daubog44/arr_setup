## Why

After fixing downloader gates, ARR service probes, and the Seerr Jellyfin auth payload, `media:post-install` still cannot initialize Seerr because Jellyfin itself is unbootstrapped. Live inspection on April 18, 2026 showed:

- `/System/Info/Public` returns `StartupWizardCompleted=false`
- `/Users/Public` returns `[]`
- Seerr Jellyfin auth now reaches Jellyfin correctly but fails with `401 INVALID_CREDENTIALS`

That means the repo currently assumes a Jellyfin admin already exists, but the deployed Jellyfin PVC can still be in first-run state with no users at all.

## What Changes

- Add an idempotent Jellyfin startup bootstrap that creates or updates the initial admin user when the startup wizard is still incomplete.
- Complete the Jellyfin startup wizard through the supported startup endpoints before Seerr tries to authenticate.
- Add focused regression coverage for the first-run detection and admin-bootstrap path.

## Capabilities

### New Capabilities

- `jellyfin-startup-bootstrap`: Define the supported first-run bootstrap contract for the repo-managed Jellyfin service.

### Modified Capabilities

- `arr-stack-surface`: Media post-install must prepare Jellyfin for Seerr by ensuring an admin account exists when Jellyfin is still in startup mode.

## Impact

- Affected code lives in [scripts/haac.py](C:/Users/Utente/OneDrive%20-%20ITS%20Tech%20Talent%20Factory/Desktop/dev/arr_setup-main/scripts/haac.py) and [tests/test_haac.py](C:/Users/Utente/OneDrive%20-%20ITS%20Tech%20Talent%20Factory/Desktop/dev/arr_setup-main/tests/test_haac.py).
- Verification must include OpenSpec validation, targeted Python unit tests, and a live `media:post-install` rerun that reaches beyond Jellyfin startup and Seerr Jellyfin authentication.
