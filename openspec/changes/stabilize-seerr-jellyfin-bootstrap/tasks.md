## 1. Seerr bootstrap payload

- [x] 1.1 Update the Seerr Jellyfin auth helper to send the required hostname, port, SSL, and server-type fields for the repo-managed Jellyfin service
- [x] 1.2 Add focused regression coverage for the Seerr Jellyfin bootstrap payload

## 2. Verification

- [x] 2.1 Validate the change with OpenSpec and targeted Python unit tests
- [x] 2.2 Rerun `media:post-install` live and confirm it progresses beyond the Seerr Jellyfin authentication step
