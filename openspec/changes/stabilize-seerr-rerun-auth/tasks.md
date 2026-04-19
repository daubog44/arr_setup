## 1. Seerr rerun auth

- [x] 1.1 Make the Seerr Jellyfin auth helper choose between first-run and rerun payloads from public settings
- [x] 1.2 Add focused regression coverage for both auth payload modes

## 2. Verification

- [x] 2.1 Validate the change with OpenSpec and targeted Python unit tests
- [x] 2.2 Rerun `media:post-install` live and confirm it progresses beyond Seerr rerun auth
