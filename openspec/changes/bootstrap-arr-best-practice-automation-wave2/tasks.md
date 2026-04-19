## 1. Downloader policy

- [ ] 1.1 Add repo-managed qBittorrent category save paths for the ARR clients through the supported WebUI API
- [ ] 1.2 Ensure the downloader manifest creates the managed category directories under `/data/torrents`

## 2. Operator contract

- [ ] 2.1 Extend media post-install verification and tests to assert the qBittorrent category contract
- [ ] 2.2 Document the supported ARR best-practice automation surface and related environment knobs

## 3. Validation

- [ ] 3.1 Validate with OpenSpec, focused unit tests, Helm render, live `media:post-install`, and qBittorrent API evidence
- [ ] 3.2 Validate the public media surfaces with the browser verifier after the post-install rerun
