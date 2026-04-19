## Design

### Inputs

- Existing `HAAC_MAIN_*`, `JELLYFIN_ADMIN_*`, and downloader credentials already used by `media:post-install`
- Current live app APIs:
  - Radarr `/api/v3/config/naming`, `/config/mediamanagement`, `/config/downloadclient`
  - Sonarr `/api/v3/config/naming`, `/config/mediamanagement`, `/config/downloadclient`
  - Lidarr `/api/v1/config/naming`, `/config/mediamanagement`, `/config/downloadclient`
  - Jellyfin `/Library/VirtualFolders`
- Current curated media directories:
  - `/data/media/movies`
  - `/data/media/tv`
  - `/data/media/music`

### Reconciliation shape

Add a small generic helper in `scripts/haac.py` for ARR config GET/PUT cycles, then apply explicit desired-state payload fragments per app:

- Radarr:
  - enable renaming
  - enable delete-empty-folders
  - enable Linux permission setting with `775`
  - keep hardlinks enabled
- Sonarr:
  - enable renaming
  - enable delete-empty-folders
  - enable Linux permission setting with `775`
  - keep hardlinks enabled
- Lidarr:
  - enable track renaming
  - enable delete-empty-folders
  - enable Linux permission setting with `775`
  - keep hardlinks enabled

Only mutate fields that are part of the documented repo-managed baseline. Do not attempt a full overwrite of each config object.

### Jellyfin

Extend `JELLYFIN_DEFAULT_LIBRARIES` so the bootstrap keeps Movies and TV intact while also ensuring a default Music library pointing at the Lidarr-managed media path.

### Documentation

Update the README to make the supported "curated media suite" explicit:

- supported and auto-bootstrapped today
- deferred pending dedicated lifecycle decisions
- rationale for not blindly importing every MediaStack-adjacent service into the default repo-managed stack

### Validation

- `openspec validate bootstrap-arr-common-settings-wave3`
- targeted Python unit tests for the new helper and desired-state payloads
- `helm template haac-stack k8s/charts/haac-stack`
- `kubectl kustomize k8s/platform`
- live `python scripts/haac.py task-run -- media:post-install`
- API verification that the common settings and Jellyfin libraries persisted
- browser verification via the existing verifier plus direct Playwright CLI checks on Jellyfin and Seerr
