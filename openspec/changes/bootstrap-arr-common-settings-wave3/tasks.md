## 1. ARR common settings

- [x] 1.1 Add repo-managed API reconciliation for Radarr, Sonarr, and Lidarr common naming and media-management settings
- [x] 1.2 Add focused regression coverage for the common-settings reconciliation helpers and desired-state payloads

## 2. Jellyfin media libraries

- [x] 2.1 Extend the repo-managed Jellyfin bootstrap so the default libraries include Lidarr-managed music
- [x] 2.2 Add focused regression coverage for the declared Jellyfin library set

## 3. Documentation and verification

- [x] 3.1 Document the curated supported media suite, the applied ARR common settings, and the rationale for deferring adjacent apps such as deprecated Readarr packaging
- [x] 3.2 Validate with OpenSpec, targeted unit tests, Helm/Kustomize renders, a live `media:post-install` rerun, API evidence, and browser verification
