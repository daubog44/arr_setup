## 1. OpenSpec and operator surface

- [x] 1.1 Add the OpenSpec deltas for a supported ARR end-to-end download verification surface
- [x] 1.2 Add a dedicated verifier task that is separate from `task up`

## 2. Verifier implementation

- [x] 2.1 Extend `scripts/haac.py` with a rerunnable verifier that proves downloader, NAS import, and Jellyfin visibility for a safe movie candidate
- [x] 2.2 Add focused unit coverage for candidate selection and end-to-end failure classification

## 3. Live validation

- [x] 3.1 Validate with OpenSpec, dry-run/render gates, and a live `media:post-install` rerun
- [x] 3.2 Run the live ARR verifier and record whether the blocker is title availability, indexer/search drift, downloader/VPN drift, import drift, or Jellyfin drift
