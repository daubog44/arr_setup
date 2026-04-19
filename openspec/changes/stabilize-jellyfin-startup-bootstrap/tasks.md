## 1. Jellyfin first-run bootstrap

- [x] 1.1 Add first-run detection for Jellyfin startup state and reconcile the initial admin user through the startup endpoints
- [x] 1.2 Add focused regression coverage for Jellyfin first-run detection and startup admin bootstrap

## 2. Verification

- [x] 2.1 Validate the change with OpenSpec and targeted Python unit tests
- [x] 2.2 Rerun `media:post-install` live and confirm it progresses beyond Jellyfin startup and Seerr Jellyfin login
