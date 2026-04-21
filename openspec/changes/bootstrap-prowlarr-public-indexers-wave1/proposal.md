## Why

The cold-cycle acceptance round proved that Prowlarr comes back without any repo-managed indexers. Seerr, Radarr, Sonarr, Lidarr, and Whisparr remain wired to Prowlarr, but the ARR verifier fails at candidate selection because Prowlarr returns zero results after a destructive `task down -> task up`.

## What Changes

- add a repo-managed Prowlarr public-indexer bootstrap surface for at least one movie-capable indexer and one TV-capable indexer
- keep the bootstrap idempotent and API-driven inside the existing post-install flow
- verify the configured indexers synchronize into the downstream ARR apps and restore the ARR end-to-end verifier after a cold cycle

## Impact

- Seerr requests can progress to real releases after a fresh bootstrap
- Prowlarr becomes the source of truth for baseline public indexers, not a manual UI step
- the operator contract gains a stronger proof that `task down -> task up` restores a usable media-request path
