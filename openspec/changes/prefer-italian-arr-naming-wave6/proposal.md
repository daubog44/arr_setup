## Why

The media stack now bootstraps and downloads end to end, but it still relies on minimal rename toggles and generic TRaSH profiles. It does not yet enforce one precise Servarr-compatible naming contract or an explicit Italian-first preference for movie and TV grabs.

## What Changes

- Add a repo-managed Italian-first media preference surface for Radarr and Sonarr using supported custom-format and quality-profile mechanics instead of ad-hoc manual settings.
- Replace boolean-only ARR naming bootstrap with explicit Radarr, Sonarr, and Lidarr naming templates that stay compatible with Servarr, TRaSH, and Jellyfin scanning.
- Keep Bazarr aligned with the same language contract and document how the Italian preference interacts with subtitles and fallback languages.
- Record the Seerr integration boundary explicitly: Seerr still brokers only Radarr and Sonarr requests, while language preference is enforced downstream by those services.

## Capabilities

### New Capabilities
- `arr-localization-and-naming`: Repo-managed Italian-first language preference and exact naming templates across the ARR media surface.

### Modified Capabilities
- `public-ui-surface`: The documented operator-facing media behavior must explain that Seerr delegates request fulfillment to Radarr and Sonarr, which enforce the language and naming policy.

## Impact

- Affected code lives in `scripts/haac.py`, `tests/test_haac.py`, `k8s/charts/haac-stack/charts/media/files/recyclarr/recyclarr.yml`, `.env.example`, and `README.md`.
- Live verification must include OpenSpec validation, targeted unit coverage, `media:post-install`, and browser/API checks against Seerr and Jellyfin.
