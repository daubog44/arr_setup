## Scope

This wave only covers baseline public Prowlarr indexers required to restore a functional request path after a cold cycle. It does not attempt to manage private tracker credentials.

## Inputs

- existing Prowlarr API key from the bootstrap runtime
- existing downstream app integrations already configured in Prowlarr
- existing FlareSolverr service surface when an indexer requires it

## Design

1. Extend the media post-install flow with an idempotent `ensure_prowlarr_indexer(...)` helper.
2. Use the live Prowlarr `/api/v1/indexer/schema` surface as the source of truth for payload shapes instead of hardcoding raw request bodies.
3. Seed a small baseline set:
   - `YTS` for public movie search
   - `EZTV` for public TV search
4. Keep configuration minimal:
   - enable the indexer
   - select the default base URL from schema when available
   - prefer magnet URLs where supported
   - leave site-specific advanced fields at schema defaults unless required for bootstrap
5. Validate through the existing cold-cycle and ARR verifier surfaces.

## Acceptance

- Prowlarr exposes repo-managed indexers after `task up` on a fresh cluster
- Radarr and Sonarr receive synced indexers from Prowlarr
- `verify:arr-flow` passes candidate selection without manual indexer setup

## Rollback

- remove the new bootstrap helper from media post-install
- delete the seeded indexers through the Prowlarr API or UI if they prove unstable
