## Why

After the downloader, ARR probe, Seerr auth, and Jellyfin first-run fixes, `media:post-install` now fails at the Seerr Jellyfin library sync stage with:

```text
API request failed: GET ... /api/v1/settings/jellyfin/library?sync=1
HTTP 404
{"message":"SYNC_ERROR_NO_LIBRARIES"}
```

Live inspection of the Jellyfin pod on April 18, 2026 showed the actual media mount paths are:

- `/data/movies`
- `/data/tv`

Jellyfin currently has no libraries configured, so Seerr has nothing to sync even though the media storage is already mounted.

## What Changes

- Add an idempotent Jellyfin library bootstrap that creates the repo-managed Movies and TV libraries when they are missing.
- Use the supported Jellyfin `Library/VirtualFolders` API with the real in-container media paths.
- Add focused regression coverage for the desired library declarations and auth-header usage.

## Capabilities

### New Capabilities

- `jellyfin-library-bootstrap`: Define the supported repo-managed Jellyfin library set for the ARR stack.

### Modified Capabilities

- `arr-stack-surface`: Media post-install must ensure Jellyfin exposes repo-managed libraries before Seerr attempts a library sync.

## Impact

- Affected code lives in [scripts/haac.py](C:/Users/Utente/OneDrive%20-%20ITS%20Tech%20Talent%20Factory/Desktop/dev/arr_setup-main/scripts/haac.py) and [tests/test_haac.py](C:/Users/Utente/OneDrive%20-%20ITS%20Tech%20Talent%20Factory/Desktop/dev/arr_setup-main/tests/test_haac.py).
- Verification must include OpenSpec validation, targeted Python unit tests, and a live `media:post-install` rerun that reaches beyond the Seerr Jellyfin library sync step.
