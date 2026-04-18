## Why

The current stack covers the core movies/TV flow, but the operational ARR suite is still thin:

- no subtitle automation
- no archive extraction helper
- no Grafana visibility for additional media utility services

The user asked for a more complete, opinionated media stack inspired by MediaStack. The first expansion wave should add the high-signal apps that directly improve the existing Jellyfin + Radarr + Sonarr use case without introducing whole new media domains that need separate libraries and provider credentials.

## What Changes

- Add Bazarr for subtitle management and wire it to Radarr/Sonarr.
- Add Unpackerr for archive extraction support on the downloader path.
- Publish the new surfaces through ingress/Homepage where appropriate and extend observability/Grafana checks for the expanded suite.

## Capabilities

### New Capabilities

- `arr-suite-expansion`: Define the first repo-managed expansion set for the ARR stack beyond the current core services.

### Modified Capabilities

- `arr-stack-surface`: The supported media stack now includes subtitle automation and downloader extraction helpers when the core movies/TV flow is enabled.

## Impact

- Affected code spans [k8s/charts/haac-stack/charts/media/templates](/C:/Users/Utente/OneDrive%20-%20ITS%20Tech%20Talent%20Factory/Desktop/dev/arr_setup-main/k8s/charts/haac-stack/charts/media/templates), [k8s/charts/haac-stack/config-templates/values.yaml.template](/C:/Users/Utente/OneDrive%20-%20ITS%20Tech%20Talent%20Factory/Desktop/dev/arr_setup-main/k8s/charts/haac-stack/config-templates/values.yaml.template), [scripts/haac.py](/C:/Users/Utente/OneDrive%20-%20ITS%20Tech%20Talent%20Factory/Desktop/dev/arr_setup-main/scripts/haac.py), [scripts/verify-public-auth.mjs](/C:/Users/Utente/OneDrive%20-%20ITS%20Tech%20Talent%20Factory/Desktop/dev/arr_setup-main/scripts/verify-public-auth.mjs), and [tests/test_haac.py](/C:/Users/Utente/OneDrive%20-%20ITS%20Tech%20Talent%20Factory/Desktop/dev/arr_setup-main/tests/test_haac.py).
- Verification must include Helm/Kustomize, live media post-install, Grafana metric presence where metrics exist, and Playwright verification of the new public surfaces.
