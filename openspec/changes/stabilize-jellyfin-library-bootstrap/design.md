## Context

The repo already mounts media into Jellyfin, but it does not yet declare the expected libraries. The live pod layout makes the intended mapping explicit:

- Movies -> `/data/movies`
- TV Shows -> `/data/tv`

Seerr depends on those Jellyfin libraries being present to discover media items, so the correct first step is to create them declaratively through the Jellyfin API.

## Goals / Non-Goals

**Goals:**
- Ensure Jellyfin has the baseline Movies and TV libraries required by the current ARR stack.
- Keep the bootstrap idempotent for reruns.
- Let Seerr library sync proceed without manual Jellyfin UI setup.

**Non-Goals:**
- This wave does not yet add anime/music/books libraries or advanced metadata tuning.
- This wave does not yet configure Jellyfin users, permissions, or plugins beyond what Seerr needs.
- This wave does not yet add extra ARR apps such as Bazarr, Readarr, or Lidarr.

## Decisions

### 1. Use Jellyfin virtual folders as the source of truth

The supported API for library creation is `POST /Library/VirtualFolders` with query parameters for `name`, `collectionType`, and `paths`. The bootstrap will query existing virtual folders first and create only the missing repo-managed ones.

Rejected alternative:
- Rely on Seerr or the Jellyfin UI to create libraries manually. That leaves `task up` incomplete and non-idempotent.

### 2. Keep the declared library set minimal and aligned to current storage

The repo-managed stack currently has concrete movie and TV flows through Radarr and Sonarr. Those two libraries are enough to unblock Seerr and keep the change narrow.

Rejected alternative:
- Add a broad media taxonomy now (anime, music, books). That belongs in a later expansion wave after the core ARR request path is stable.

## Risks / Trade-offs

- [Risk] Some operators may prefer different library names. -> Mitigation: the first move optimizes for the repo-managed default; customization can be layered later once the bootstrap contract is stable.
- [Risk] Library creation could fail if the mounted paths disappear. -> Mitigation: use the real in-container paths observed live and surface explicit API errors if creation fails.
