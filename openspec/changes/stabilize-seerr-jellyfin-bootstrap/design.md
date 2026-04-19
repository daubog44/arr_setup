## Context

The repo already has the right general sequence for Seerr bootstrap:

1. ensure the core media services are reachable
2. sign in to Seerr through the Jellyfin auth path
3. persist Jellyfin, Radarr, and Sonarr settings inside Seerr
4. finish initialization

The live failure is narrow: step 2 posts an incomplete payload. Seerr's own setup UI and server route require Jellyfin connection fields during `/api/v1/auth/jellyfin`, because Seerr may be unconfigured at that point and cannot infer the server endpoint from persisted settings yet.

## Goals / Non-Goals

**Goals:**
- Send the correct Jellyfin bootstrap payload to Seerr.
- Keep the internal bootstrap path pointed at the in-cluster Jellyfin service.
- Preserve the existing external hostname publication after successful login.

**Non-Goals:**
- This wave does not yet automate TRaSH/Recyclarr profiles.
- This wave does not add new ARR services such as Bazarr, Readarr, or Lidarr.
- This wave does not redesign Seerr's later Radarr/Sonarr payload selection.

## Decisions

### 1. Bootstrap Seerr against the in-cluster Jellyfin endpoint

During first-time setup Seerr should authenticate against `jellyfin.media.svc.cluster.local:80` with `useSsl=false` and `serverType=1` (Jellyfin). That matches the repo-managed topology and avoids depending on external ingress or Authelia inside the bootstrap path.

Rejected alternative:
- Bootstrap Seerr against the public Jellyfin URL. This would add ingress and auth dependencies to a path that can stay entirely in-cluster.

### 2. Keep external URL publication separate from initial login

The initial Jellyfin auth payload only needs the internal service address. After login succeeds, the existing settings write can continue to publish the external Jellyfin hostname into Seerr for user-facing links.

Rejected alternative:
- Collapse login and settings persistence into one step. That would hide the failure boundary and make Seerr bootstrap harder to diagnose.

## Risks / Trade-offs

- [Risk] Seerr could change the numeric `serverType` contract in a future release. -> Mitigation: pin regression coverage to the current required Jellyfin bootstrap fields and cite the upstream contract in this change.
- [Risk] Jellyfin internal service routing could change if the chart topology changes. -> Mitigation: keep the internal hostname explicit in one helper so future service renames are localized.
