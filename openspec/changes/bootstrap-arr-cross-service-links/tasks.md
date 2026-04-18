## 1. Service wiring

- [x] 1.1 Add idempotent helpers for Radarr and Sonarr qBittorrent download-client reconciliation
- [x] 1.2 Add idempotent helpers for Prowlarr qBittorrent download-client and Radarr/Sonarr application reconciliation
- [x] 1.3 Extend `reconcile_media_stack()` so the core wiring is applied on every `media:post-install` rerun

## 2. Verification

- [x] 2.1 Add focused regression coverage for create-vs-update service-link behavior
- [x] 2.2 Validate the change with OpenSpec, targeted unit tests, and a live `task media:post-install` rerun
