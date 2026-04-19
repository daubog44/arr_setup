## Why

The current curated media suite covers movies, TV, music, subtitles, requests, and download orchestration, but it does not yet include an adult-media ARR surface. The operator explicitly wants Whisparr added with the same shared NAS, downloader, and Prowlarr conventions used elsewhere in the stack.

## What Changes

- Add Whisparr as a repo-managed workload in the media namespace with persistent config, shared `/data` storage, and a published route.
- Wire Whisparr to the existing repo-managed Prowlarr and qBittorrent or SABnzbd download paths with a dedicated category and root folder.
- Keep Whisparr isolated from Seerr, because Seerr does not support Whisparr upstream.
- Add any supported observability surface; if no supported exporter exists, record that limit explicitly instead of inventing unsupported metrics.

## Capabilities

### New Capabilities
- `whisparr-stack-surface`: Repo-managed Whisparr workload, downloader wiring, and published operator surface.

### Modified Capabilities
- `public-ui-surface`: The published media catalog must include Whisparr only if the route is repo-managed and verification-covered.

## Impact

- Affected code lives in `k8s/charts/haac-stack/`, `scripts/haac.py`, `tests/test_haac.py`, and the media docs.
- Live verification must include route reachability, Whisparr bootstrap, and downloader path validation without claiming Seerr integration.
