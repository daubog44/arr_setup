## Why

The Seerr bootstrap is now functional and rerunnable, but live evidence from April 19, 2026 still shows one repo-managed gap in the persisted main settings:

- `GET /api/v1/settings/public` reports `initialized=true`
- the live runtime file `/app/config/settings.json` still has `"applicationUrl": ""`
- Seerr's admin API exposes `/api/v1/settings/main`, so this setting can be reconciled through a supported path instead of manual UI edits

The operator explicitly asked for Seerr to be set up automatically through post-install. Leaving `applicationUrl` blank means notification and reset-link surfaces still do not have the correct public app URL, even though the rest of the Seerr/Jellyfin/Radarr/Sonarr contract is already automated.

## What Changes

- Extend `media:post-install` so Seerr reconciles its repo-managed main settings through the supported admin API.
- Persist the public Seerr application URL after admin login, using the repo-managed domain contract.
- Add focused regression coverage and operator-facing docs for the additional Seerr bootstrap behavior.

## Capabilities

### New Capabilities

- `seerr-main-settings-bootstrap`: Define the repo-managed Seerr main-settings baseline that must be present after the media bootstrap rerun.

### Modified Capabilities

- `arr-stack-surface`: Seerr bootstrap now includes the public application URL, not only Jellyfin and ARR service wiring.

## Impact

- Affected code lives primarily in [scripts/haac.py](/C:/Users/Utente/OneDrive%20-%20ITS%20Tech%20Talent%20Factory/Desktop/dev/arr_setup-main/scripts/haac.py), [tests/test_haac.py](/C:/Users/Utente/OneDrive%20-%20ITS%20Tech%20Talent%20Factory/Desktop/dev/arr_setup-main/tests/test_haac.py), and [README.md](/C:/Users/Utente/OneDrive%20-%20ITS%20Tech%20Talent%20Factory/Desktop/dev/arr_setup-main/README.md).
- Verification must include OpenSpec validation, targeted unit tests, a live `media:post-install` rerun, runtime evidence that Seerr's main settings persist the public URL, and browser verification of the public Seerr surface.
