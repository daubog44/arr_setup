## Context

Radarr and Sonarr already run with the repo-managed media host path mounted inside their containers, but Seerr cannot auto-wire them unless the applications themselves expose at least one root folder through their APIs.

The current bootstrap assumes those root folders already exist. That assumption is wrong on a fresh PVC and breaks idempotent ARR setup.

## Goals / Non-Goals

**Goals:**
- Create the supported Radarr and Sonarr root folders when they are absent.
- Keep the topology explicit and local to the media bootstrap path.
- Make reruns harmless when the folders already exist.

**Non-Goals:**
- This wave does not add TRaSH/Recyclarr custom formats or quality profile syncing yet.
- This wave does not change download clients, remote path mappings, or Seerr quality-profile policy.

## Decisions

### 1. Bootstrap root folders via the ARR APIs

Use the official `POST /api/v3/rootfolder` endpoint against Radarr and Sonarr before asking Seerr for ARR option discovery. The bootstrap should create:

- Radarr: `/data/media/movies`
- Sonarr: `/data/media/tv`

If the desired folder already exists, the helper must no-op and return the existing list.

Rejected alternative:
- Patch Seerr to accept empty root-folder lists. That would hide a real ARR configuration gap and still leave future requests without a valid import destination.

## Risks / Trade-offs

- [Risk] The media mount topology could change later. -> Mitigation: keep the paths centralized in one helper so a future topology wave only needs one contract update.
