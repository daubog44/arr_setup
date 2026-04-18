## Why

Live validation on April 18, 2026 showed that the downloader surface is not converged on the repo-managed shared storage model even though `media:post-install` currently reaches a green path.

Evidence from the running qBittorrent pod:

- the pod mounts the shared host path at `/data`
- the real shared download directories present in the container are `/data/torrents` and `/data/torrents/incomplete`
- the persisted qBittorrent configuration still points `Downloads\\SavePath=/downloads/` and `Downloads\\TempPath=/downloads/incomplete/`
- `/downloads` and `/downloads/incomplete` do not exist in the container filesystem

That mismatch means the ARR stack is relying on an invalid downloader path contract. Bazarr and Unpackerr should not be added on top of that inconsistency.

## What Changes

- Define the supported qBittorrent download paths explicitly under the shared `/data/torrents` surface.
- Reconcile qBittorrent preferences and category paths during the supported media post-install flow instead of relying on whatever the image defaults persist.
- Add regression coverage plus live verification that the downloader path surface converges before the ARR expansion wave consumes it.

## Capabilities

### New Capabilities

- `downloaders-shared-paths`: Define the supported qBittorrent shared-path contract for the repo-managed media topology.

### Modified Capabilities

- `arr-stack-surface`: Media post-install MUST converge downloader paths on the shared storage model before higher-level ARR integrations rely on them.

## Impact

- Affected code lives in [scripts/haac.py](C:/Users/Utente/OneDrive%20-%20ITS%20Tech%20Talent%20Factory/Desktop/dev/arr_setup-main/scripts/haac.py), [k8s/charts/haac-stack/charts/downloaders/templates/downloaders.yaml](C:/Users/Utente/OneDrive%20-%20ITS%20Tech%20Talent%20Factory/Desktop/dev/arr_setup-main/k8s/charts/haac-stack/charts/downloaders/templates/downloaders.yaml), and [tests/test_haac.py](C:/Users/Utente/OneDrive%20-%20ITS%20Tech%20Talent%20Factory/Desktop/dev/arr_setup-main/tests/test_haac.py).
- Verification must include OpenSpec validation, targeted unit coverage, Helm rendering, and a live `task media:post-install` rerun that leaves qBittorrent on real shared paths under `/data`.
