## Context

The MediaStack catalog is broad, but not every app belongs in the repo-managed first expansion wave. The current HaaC stack already covers:

- Jellyfin
- Radarr
- Sonarr
- Prowlarr
- qBittorrent/QUI
- Autobrr
- Seerr
- FlareSolverr

The highest-value additions for the current Movies/TV-first topology are:

- Bazarr: integrates directly with Radarr and Sonarr and improves actual playback quality in Jellyfin
- Unpackerr: complements qBittorrent for extracted-release workflows without requiring a separate media domain

Apps such as Lidarr, Readarr, Mylar, SABnzbd, and Tdarr are valid future candidates, but they need either new libraries, new providers, or significantly more operational surface. They should be follow-up waves rather than getting mixed into the first completion pass.

## Goals / Non-Goals

**Goals:**
- Add Bazarr and Unpackerr with repo-managed manifests and bootstrap integration.
- Keep the configuration aligned to the existing `/data/media/*` topology.
- Expose observability for any native metrics that exist or can be scraped safely.

**Non-Goals:**
- This wave does not add every app from MediaStack.
- This wave does not introduce Usenet because provider credentials are not part of the current repo contract.
- This wave does not add music/books/comics library managers yet.

## Decisions

### 1. Expand only the apps that strengthen the current movies/TV path

Add:

- Bazarr
- Unpackerr

Reject for this wave:

- Lidarr / Readarr / Mylar / Whisparr / Tdarr / SABnzbd

Reason:
- they either require new media libraries or a bigger credential/provider surface than the current repo-managed stack guarantees

### 2. Bootstrap integrations through the same post-install path

Bazarr should be wired to Radarr and Sonarr through API/bootstrap logic just like Seerr is. Unpackerr should derive its connection details from the existing downloader and ARR topology.

### 3. Observability follows real metrics only

If a service exposes native metrics or a safe exporter path, wire it into Prometheus/Grafana. If it does not, verify it through HTTP/browser reachability instead of inventing fake metrics.

## Risks / Trade-offs

- [Risk] Bazarr API/bootstrap semantics may differ from the current ARR helpers. -> Mitigation: verify against the live service and keep the wave scoped to one subtitle app.
- [Risk] Unpackerr adds another long-running process in the media namespace. -> Mitigation: keep its configuration minimal and tied to the current downloader/ARR services only.
