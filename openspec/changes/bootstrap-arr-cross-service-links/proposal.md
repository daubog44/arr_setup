## Why

`media:post-install` now proves that the downloader pod, Jellyfin bootstrap, Seerr initialization, and ARR root folders are healthy enough to rerun. The live stack is still not operational as an integrated ARR surface because the cross-service links remain empty:

- Radarr download clients: `0`
- Sonarr download clients: `0`
- Prowlarr applications: `0`
- Prowlarr download clients: `0`

This means requests can be approved in Seerr, but neither Radarr nor Sonarr can actually hand work to qBittorrent, and Prowlarr cannot sync indexers into the downstream services.

## What Changes

- Add idempotent post-install reconciliation for qBittorrent download clients in Radarr and Sonarr.
- Add idempotent Prowlarr reconciliation for the qBittorrent download client plus Radarr and Sonarr application links.
- Reuse the existing repo-managed downloader credentials and internal cluster URLs instead of introducing another credential surface.

## Capabilities

### New Capabilities

- `arr-cross-service-links`: Define the required Radarr/Sonarr/Prowlarr/qBittorrent topology for the repo-managed ARR stack.

### Modified Capabilities

- `arr-stack-surface`: Media post-install MUST wire the core ARR applications together, not only verify they are individually reachable.

## Impact

- Affected code lives in [scripts/haac.py](/C:/Users/Utente/OneDrive%20-%20ITS%20Tech%20Talent%20Factory/Desktop/dev/arr_setup-main/scripts/haac.py) and [tests/test_haac.py](/C:/Users/Utente/OneDrive%20-%20ITS%20Tech%20Talent%20Factory/Desktop/dev/arr_setup-main/tests/test_haac.py).
- Verification must include OpenSpec validation, targeted unit coverage, and a live `task media:post-install` rerun that leaves the four service-link surfaces populated.
