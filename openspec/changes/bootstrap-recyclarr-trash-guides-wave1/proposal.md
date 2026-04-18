## Why

The repo already ships a `media/recyclarr` CronJob and image pin, but it still creates only the default placeholder config. Live ARR state shows that Radarr and Sonarr are operating on their stock quality profiles (`Any`, `HD-720p`, `HD-1080p`, `Ultra-HD`, `WEB-1080p`) rather than a deliberate TRaSH/Recyclarr policy.

That leaves the media stack operational but not opinionated. The user specifically asked for best-practice/TRaSH setup, so the repo needs a first-class quality-sync contract instead of a dormant container.

## What Changes

- Add a repo-managed Recyclarr config template based on official template patterns.
- Generate only the runtime `secrets.yml` from the live ARR API keys instead of persisting mutable config in a PVC.
- Sync a curated 1080p-focused TRaSH profile set into Sonarr v4 and Radarr v5.
- Fold Recyclarr into the supported media post-install flow so fresh clusters converge immediately instead of waiting for the weekly CronJob.

## Capabilities

### New Capabilities

- `arr-quality-policy-sync`: Define the repo-managed quality-profile and custom-format sync contract for Radarr and Sonarr.

### Modified Capabilities

- `arr-stack-surface`: Media post-install MUST converge the supported quality-policy defaults, not only the app connectivity.

## Impact

- Affected code lives in [scripts/haac.py](/C:/Users/Utente/OneDrive%20-%20ITS%20Tech%20Talent%20Factory/Desktop/dev/arr_setup-main/scripts/haac.py), [tests/test_haac.py](/C:/Users/Utente/OneDrive%20-%20ITS%20Tech%20Talent%20Factory/Desktop/dev/arr_setup-main/tests/test_haac.py), and [k8s/charts/haac-stack/charts/media/templates/helpers.yaml](/C:/Users/Utente/OneDrive%20-%20ITS%20Tech%20Talent%20Factory/Desktop/dev/arr_setup-main/k8s/charts/haac-stack/charts/media/templates/helpers.yaml).
- Verification must include unit coverage, Helm rendering, a live `task media:post-install` rerun, and evidence that Recyclarr updated Radarr/Sonarr successfully.
