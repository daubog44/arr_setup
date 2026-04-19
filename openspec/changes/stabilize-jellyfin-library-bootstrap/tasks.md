## 1. Jellyfin libraries

- [x] 1.1 Add an idempotent Jellyfin library bootstrap for Movies and TV using the real in-container media paths
- [x] 1.2 Add focused regression coverage for the declared Jellyfin library set and auth headers

## 2. Verification

- [x] 2.1 Validate the change with OpenSpec and targeted Python unit tests
- [x] 2.2 Rerun `media:post-install` live and confirm it progresses beyond Jellyfin library sync
