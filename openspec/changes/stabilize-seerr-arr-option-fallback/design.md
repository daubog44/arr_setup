## Context

Seerr is the operator-facing integration surface for ARR onboarding, but its Sonarr option discovery can lag behind real ARR state because the upstream code caches `/rootfolder` results for 3600 seconds. The bootstrap cannot wait an hour after creating root folders.

The repo already has a trusted local path to Radarr and Sonarr via port-forward plus service API keys, so the smallest reliable fix is to treat Seerr test responses as preferred-but-not-authoritative for root-folder discovery.

## Goals / Non-Goals

**Goals:**
- Recover from stale empty Seerr root-folder test responses.
- Keep Seerr settings payload generation deterministic.
- Reuse direct ARR state only where Seerr cache is known to be unreliable.

**Non-Goals:**
- This wave does not patch Seerr upstream.
- This wave does not add TRaSH/Recyclarr profile syncing yet.

## Decisions

### 1. Use direct ARR root folders as a fallback only

Continue to call Seerr test endpoints for quality profiles, tags, and base URLs, but if `rootFolders` is empty while direct ARR root folders are known, merge in the direct root-folder list before selecting the preferred directory.

Rejected alternative:
- Sleep and retry until Seerr cache expires. That would make bootstrap nondeterministic and far too slow.

## Risks / Trade-offs

- [Risk] Direct ARR and Seerr could disagree temporarily on more than root folders. -> Mitigation: constrain the fallback to root folders only and keep profile selection on the Seerr-tested data path.
