## Why

Homepage now renders the operator dashboard again, but two repo-managed preview widgets still fail in live use:

- the Grafana card shows `HTTP status 500` and `API Error Information`
- the qBittorrent card shows `API Error Information`

Live evidence shows these are real wiring defects, not cosmetic noise:

- Homepage logs show the Grafana widget calling the internal `http://kube-prometheus-stack-grafana...` surface and failing on a redirect to `https`, while Grafana basic auth is disabled.
- The downloaders `port-sync` sidecar waits forever for an unauthenticated `200` from qBittorrent's `/api/v2/app/version`, so the qBittorrent password never reconciles and Homepage cannot log in to the API.
- Even when the widget secrets change, Homepage and the downloader stack do not roll automatically, so secret-driven widget auth can drift across pod restarts.

## What Changes

- Wire the Grafana Homepage widget to a protocol/auth surface that matches the live Grafana configuration.
- Fix the qBittorrent bootstrap so the desired WebUI password is enforced declaratively and recovery does not depend on temporary-password log scraping alone.
- Add secret-driven rollout checks so Homepage and downloaders actually restart when widget credentials change.
- Tighten browser verification so Homepage widget API failures break the operator verification path.

## Impact

- Homepage cards for Grafana and qBittorrent regain working previews instead of surfacing internal widget failures.
- The repo catches widget regressions during browser validation instead of relying on manual inspection.
