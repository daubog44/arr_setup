## Why

The ARR root-folder bootstrap is necessary but not sufficient to make `media:post-install` pass. Live validation on April 18, 2026 now shows:

- direct `GET /api/v3/rootfolder` on Radarr returns `/data/media/movies`
- direct `GET /api/v3/rootfolder` on Sonarr returns `/data/media/tv`
- Seerr `POST /api/v1/settings/radarr/test` returns the Radarr root folder correctly
- Seerr `POST /api/v1/settings/sonarr/test` still returns `rootFolders=[]`

Official Seerr source explains why:

- [`server/routes/settings/sonarr.ts`](https://github.com/seerr-team/seerr/blob/main/server/routes/settings/sonarr.ts) builds `rootFolders` from `sonarr.getRootFolders()`
- [`server/api/servarr/base.ts`](https://github.com/seerr-team/seerr/blob/main/server/api/servarr/base.ts) resolves `getRootFolders()` via `getRolling('/rootfolder', ..., 3600)`

That means Seerr can cache a stale empty Sonarr root-folder list for up to an hour after bootstrap creates the folder.

## What Changes

- Add a direct ARR API fallback for root-folder option discovery when Seerr test responses are stale or empty.
- Reuse the already-verified ARR service API keys and live root-folder topology instead of trusting Seerr cache blindly.
- Add regression coverage for stale Seerr test responses.

## Capabilities

### New Capabilities

- `seerr-arr-option-fallback`: Define how media bootstrap recovers when Seerr ARR test responses lag behind direct ARR state.

### Modified Capabilities

- `arr-stack-surface`: Media post-install must progress even when Seerr test endpoints return stale empty root-folder lists.

## Impact

- Affected code lives in [scripts/haac.py](C:/Users/Utente/OneDrive%20-%20ITS%20Tech%20Talent%20Factory/Desktop/dev/arr_setup-main/scripts/haac.py) and [tests/test_haac.py](C:/Users/Utente/OneDrive%20-%20ITS%20Tech%20Talent%20Factory/Desktop/dev/arr_setup-main/tests/test_haac.py).
- Verification must include OpenSpec validation, targeted Python unit tests, and a live `media:post-install` rerun that progresses beyond Seerr ARR option discovery.
