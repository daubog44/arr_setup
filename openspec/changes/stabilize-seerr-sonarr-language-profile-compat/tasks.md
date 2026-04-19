## 1. Sonarr payload compat

- [x] 1.1 Omit absent language-profile fields from the Seerr Sonarr bootstrap payload
- [x] 1.2 Add focused regression coverage for Sonarr test responses without language profiles

## 2. Verification

- [x] 2.1 Validate the change with OpenSpec and targeted Python unit tests
- [x] 2.2 Rerun `media:post-install` live and confirm it progresses beyond Sonarr settings persistence
