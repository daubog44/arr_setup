## 1. Downloader readiness and reporting

- [x] 1.1 Relax the downloader pre-bootstrap gate so it proceeds on the real qBittorrent/QUI steady-state contract instead of timing out before the actual bootstrap logic runs
- [x] 1.2 Tighten the ProtonVPN blocker detector so generic healthy OpenVPN lines do not masquerade as credential or subscription failures

## 2. Verification

- [x] 2.1 Add focused regression coverage for downloader readiness success and false Proton blocker suppression
- [x] 2.2 Validate the change with OpenSpec, targeted Python unit tests, and a live `media:post-install` rerun that reaches beyond the downloader bootstrap gate
