## 1. Downloader path model

- [x] 1.1 Define the supported qBittorrent save/temp paths under `/data/torrents` and reconcile them during bootstrap
- [x] 1.2 Ensure the downloader path contract is visible in the repo-managed Kubernetes manifests and Python bootstrap helpers

## 2. Verification

- [x] 2.1 Add focused regression coverage for downloader path reconciliation
- [x] 2.2 Validate with OpenSpec, targeted unit tests, Helm render, and a live `task media:post-install` rerun
