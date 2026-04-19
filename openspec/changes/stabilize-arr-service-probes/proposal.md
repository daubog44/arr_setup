## Why

`media:post-install` now reaches the `Media service probes` stage, but it still fails on April 18, 2026 because the probe contract in `scripts/haac.py` is stale. Live port-forward checks against the repo-managed services showed:

- `radarr /ping` returns HTTP `200` with `{"status":"OK"}`
- `sonarr /ping` returns HTTP `200` with `{"status":"OK"}`
- `prowlarr /ping` returns HTTP `200` with `{"status":"OK"}`

The current bootstrap still requires the body pattern `pong`, so it reports a false failure even when the ARR applications are healthy.

## What Changes

- Stabilize the ARR service probe contract so Radarr, Sonarr, and Prowlarr accept the actual healthy `/ping` response body returned by the deployed app versions.
- Add focused regression coverage so future image bumps do not silently restore the stale `pong` expectation.
- Revalidate `media:post-install` live so the operator path can proceed past the service-probe phase.

## Capabilities

### New Capabilities

- `arr-service-probes`: Define the supported health-probe contract for the repo-managed ARR applications during media post-install reconciliation.

### Modified Capabilities

- `arr-stack-surface`: The repo-managed ARR stack bootstrap must accept the actual healthy service probe body returned by the deployed applications.

## Impact

- Affected code lives in [scripts/haac.py](C:/Users/Utente/OneDrive%20-%20ITS%20Tech%20Talent%20Factory/Desktop/dev/arr_setup-main/scripts/haac.py) and [tests/test_haac.py](C:/Users/Utente/OneDrive%20-%20ITS%20Tech%20Talent%20Factory/Desktop/dev/arr_setup-main/tests/test_haac.py).
- Verification must include OpenSpec validation, targeted Python unit tests, and a live `media:post-install` rerun that reaches beyond the ARR service probes.
