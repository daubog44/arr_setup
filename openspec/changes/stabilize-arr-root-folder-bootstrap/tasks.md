## 1. ARR root folders

- [x] 1.1 Add idempotent Radarr and Sonarr root-folder bootstrap helpers using the supported `/data/media/*` paths
- [x] 1.2 Add focused regression coverage for missing-vs-existing root-folder behavior

## 2. Verification

- [x] 2.1 Validate the change with OpenSpec and targeted Python unit tests
- [x] 2.2 Rerun `media:post-install` live and confirm it progresses beyond Seerr ARR option discovery
