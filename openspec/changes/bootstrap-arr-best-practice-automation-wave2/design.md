## Context

The current repo already bootstraps most of the core movies/TV surfaces:

- qBittorrent save/temp paths are converged on `/data/torrents`
- Radarr, Sonarr, and Prowlarr are configured through internal service endpoints
- Seerr is wired to Jellyfin plus the repo-managed ARR services
- Bazarr language defaults and Recyclarr quality/custom-format sync already run in `media:post-install`

What is still implicit is the downloader-side category routing. Radarr and Sonarr send category names to qBittorrent, but qBittorrent itself is not yet reconciled to own those categories and save paths declaratively.

Official qBittorrent WebUI API documentation for v4.1-v4.6.x exposes:

- `/api/v2/auth/login` for cookie-based auth
- `/api/v2/torrents/categories` to list current categories
- `/api/v2/torrents/createCategory` and `/api/v2/torrents/editCategory` with `savePath` support

That makes category reconciliation a supported operator action rather than an image-specific hack.

## Goals / Non-Goals

**Goals**

- Reconcile the qBittorrent ARR categories through the supported WebUI API.
- Keep all category save paths under the shared `/data/torrents` tree.
- Document the resulting best-practice contract so the operator understands what is managed automatically.

**Non-Goals**

- This wave does not add new media domains such as music or books yet.
- This wave does not replace Recyclarr with another policy engine.

## Decisions

### 1. Keep one shared torrents root, but make categories explicit

The stack will keep:

- default save path: `/data/torrents`
- temp path: `/data/torrents/incomplete`

And add explicit category save paths:

- `radarr` -> `/data/torrents/radarr`
- `tv-sonarr` -> `/data/torrents/tv-sonarr`
- `prowlarr` -> `/data/torrents/prowlarr`
- imported categories when supported -> matching subpaths under `/data/torrents/*-imported`

This preserves the shared-volume hardlink-friendly model while making the downloader routing explicit and inspectable.

### 2. Bootstrap categories through the live qBittorrent API

`media:post-install` should:

1. authenticate to qBittorrent with the repo-managed downloader credentials
2. list current categories
3. create or edit the managed categories until the desired save paths match
4. fail closed if the category contract cannot be persisted

### 3. Document the operator-managed policy surface

The README should state which ARR settings are managed automatically today:

- downloader auth
- qBittorrent paths and categories
- Radarr/Sonarr/Prowlarr internal links
- Seerr + Jellyfin bootstrap
- Bazarr language defaults
- Recyclarr/TRaSH sync expectations

## Risks / Trade-offs

- qBittorrent category save paths can move future torrents when categories change. Keeping the directories under the same shared root limits blast radius.
- Existing torrents in the generic root are not migrated by this wave. The contract applies to newly managed downloads unless a future migration wave is opened.
