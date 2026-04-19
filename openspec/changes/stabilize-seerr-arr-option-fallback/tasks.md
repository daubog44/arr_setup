## 1. ARR option discovery fallback

- [x] 1.1 Add a direct ARR root-folder fallback path for Seerr Radarr/Sonarr settings bootstrap
- [x] 1.2 Add focused regression coverage for stale-empty Seerr root-folder responses

## 2. Verification

- [x] 2.1 Validate the change with OpenSpec and targeted Python unit tests
- [x] 2.2 Rerun `media:post-install` live and confirm it progresses beyond Seerr ARR option discovery
