# Media Stack Reference

This guide explains the supported request-to-playback flow for the repo-managed media stack.

## Supported Suite

The curated stack in this repo is:

- Seerr
- Jellyfin
- Prowlarr
- Radarr
- Sonarr
- Lidarr
- Whisparr
- Bazarr
- qBittorrent
- QUI
- SABnzbd
- Autobrr
- FlareSolverr
- Recyclarr
- Unpackerr

These apps are not all interchangeable. Each owns a specific part of the flow.

## Request To Playback Flow

The supported happy path is:

1. discovery/request
   - Seerr presents movies and TV content to users
   - Jellyfin library sync tells Seerr what is already owned
2. request handoff
   - Seerr sends movie requests to Radarr
   - Seerr sends series requests to Sonarr
3. indexer and release discovery
   - Prowlarr owns indexers
   - Prowlarr syncs those indexers into supported downstream apps
   - FlareSolverr only helps supported challenge-protected indexers
4. download execution
   - Radarr/Sonarr/Lidarr/Whisparr send jobs to qBittorrent or SABnzbd
   - qBittorrent runs through Gluetun/ProtonVPN on the supported torrent path
5. import and organization
   - ARR apps import completed files into the NAS-backed media roots
   - hardlinks stay enabled so import is fast and storage-friendly
6. library surfacing
   - Jellyfin libraries expose the imported media for playback

## What Seerr Does And Does Not Do

Seerr is a request broker. It is not an indexer manager.

In this repo Seerr is bootstrapped against:

- Jellyfin
- Radarr
- Sonarr
- its public application URL

It does not own:

- indexer definitions
- release search tuning
- Lidarr or Whisparr request surfaces

That means:

- Movies and TV are managed directly through Seerr
- Music and adult-media stay outside the Seerr UI contract
- Lidarr and Whisparr still work, but their requests/search/import flow happens in their own ARR UIs plus Prowlarr

This matches Seerr's documented contract today: it integrates with Jellyfin/Plex/Emby and with Radarr/Sonarr, not with Lidarr or Whisparr as first-class request targets.

## Where Indexers Actually Live

Prowlarr is the indexer source of truth.

The repo-managed bootstrap wires Prowlarr to downstream apps so indexers can be synchronized into:

- Radarr
- Sonarr
- Lidarr
- Whisparr

When you want to inspect or debug indexers:

- use Prowlarr to manage indexer definitions, health, proxy/challenge support, and app sync
- use Radarr/Sonarr/Lidarr/Whisparr interactive search to see actual releases considered for a title
- use Seerr only for request/discovery on movies and TV

If you want to see what is currently downloadable:

- Seerr shows requestable movie/series titles, not raw tracker releases
- Prowlarr search shows raw indexer/search results
- the downstream ARR app shows manual or interactive search results for the target movie/series/artist/title

## Italian-First Defaults

This repo is biased toward Italian media first, with English as fallback where supported.

Repo-managed defaults:

- `ARR_PREFERRED_AUDIO_LANGUAGES=it,en`
- `BAZARR_LANGUAGES=it,en`
- Jellyfin defaults:
  - `UICulture=it-IT`
  - `MetadataCountryCode=IT`
  - `PreferredMetadataLanguage=it`

The Italian-first behavior is enforced in Radarr and Sonarr through repo-managed quality/custom-format scoring, not by vague UI defaults alone.

## Naming And Import Best Practices

The repo-managed ARR bootstrap enforces the common media-management posture expected by Servarr/TRaSH-style setups:

- renaming enabled
- hardlinks enabled
- empty folder cleanup enabled
- Linux permission management enabled
- deterministic root-folder and category routing

Key naming defaults from the Go-native `haac reconcile-media-stack` behavior:

- Radarr movie folder format:
  - `{Movie CleanTitle} ({Release Year})`
- Whisparr movie folder format:
  - `Movies/{Movie CleanTitle} ({Release Year})`

The repo-managed behavior intentionally favors clean, stable folders while leaving richer quality/custom-format detail to the imported file name and downstream metadata.

## Downloader And Storage Contract

The downloader path is shared-path and NAS-backed by design.

Torrent/usenet staging lives under `/data` inside the media workloads, and final imports land on the NAS-backed media roots that are mounted from Proxmox into the K3s nodes.

That means the actual ownership path is:

1. Proxmox mounts the NAS share
2. the share is bind-mounted into the LXC nodes
3. K3s workloads use those node-mounted paths
4. ARR imports target those NAS-backed roots

The result is that the final media library lives on the NAS, not inside ephemeral pod storage.

## Operational Commands

Useful supported commands:

- `task media:post-install`
  - reruns downloader/bootstrap/app wiring
- `task verify:arr-flow`
  - validates the request-to-playback path
- `task verify-all`
  - verifies the broader public/operator surface
