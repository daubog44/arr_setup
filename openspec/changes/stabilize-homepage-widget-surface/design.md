## Design

### Evidence

- Homepage pod logs repeatedly report `ERR_FR_REDIRECTION_FAILURE` while proxying the Grafana widget because the widget calls the internal HTTP service and Grafana redirects toward HTTPS.
- The Grafana chart explicitly sets:
  - `server.root_url = https://grafana.${DOMAIN_NAME}`
  - `auth.disable_login_form = true`
  - `auth.basic.enabled = false`
- Homepage's internal Grafana proxy endpoints return `200` after the basic-auth/site-monitor fixes, so the remaining widget failure is no longer the Grafana data path.
- The Homepage qBittorrent widget uses the same secret as the downloader stack, but live Homepage logs still show `Error logging in to qBittorrent`, and the qBittorrent widget proxy returns `403`.
- The live `port-sync` container is still running the old readiness contract that waits forever for `curl -fsS http://127.0.0.1:8080/api/v2/app/version`, even though the endpoint now returns `403` before authentication.
- Live qBittorrent state under `/config/qBittorrent/qBittorrent.conf` has no persisted `WebUI\Password_PBKDF2` entry, so password convergence still depends on runtime recovery.

### Solution shape

1. Grafana widget surface
   - Enable Grafana basic auth again for API/widget use.
   - Keep the Homepage Grafana widget on the in-cluster service URL for the authenticated API calls.
   - Move the Grafana Homepage site monitor to the public HTTPS URL so the card-level reachability check does not trip over internal HTTP-to-HTTPS redirection.

2. qBittorrent bootstrap surface
   - Keep the desired password source unchanged.
   - Change the `port-sync` readiness wait so it accepts qBittorrent's authenticated-ready `403` on `/api/v2/app/version`.
   - Generate a qBittorrent-compatible `WebUI\Password_PBKDF2` hash from the existing secret-backed password during repo secret generation.
   - Preseed `/config/qBittorrent/qBittorrent.conf` from an init container before qBittorrent starts, so the desired WebUI password exists even when temporary-password logs are unavailable.
   - Keep the API-based recovery flow as a fallback, but remove it from the critical path for steady-state convergence.

3. Secret-driven rollouts
   - Add a Homepage pod-template checksum for `homepage-widgets-secret`.
   - Add a downloaders pod-template checksum for `downloaders-auth`, so qBittorrent and its sidecars actually restart when the declarative password changes.

4. Browser contract
   - Extend `scripts/verify-public-auth.mjs` so the Homepage route fails when widget cards still surface `API Error Information` or `HTTP status 500`.

### Risks

- Re-enabling Grafana basic auth makes the admin credential usable against the Grafana HTTP API again.
  - Mitigation: keep Homepage API traffic on the cluster-local service surface, keep OIDC as the browser login path, and record this as a residual security tradeoff for future least-privilege follow-up.
- Deterministically generating a qBittorrent PBKDF2 hash means the sealed secret will stay stable for the same password instead of changing on every render.
  - Mitigation: derive the salt from the secret input so the rendered GitOps output stays idempotent across reruns while still using the qBittorrent PBKDF2 format.
- Homepage widget checks rely on stable card text for Grafana and qBittorrent.
  - Mitigation: fail on the generic widget error markers that are already rendered to operators today.

### Verification

- `openspec validate stabilize-homepage-widget-surface`
- `python scripts/haac.py generate-secrets-local --kubeconfig C:\Users\Utente\.kube\haac-k3s.yaml --kubectl .tools\windows-amd64\bin\kubectl.exe`
- `.tools\windows-amd64\bin\helm.exe template haac-stack k8s\charts\haac-stack > $null`
- `.tools\windows-amd64\bin\kubectl.exe kustomize k8s\platform > $null`
- `node --check scripts/verify-public-auth.mjs`
- `python scripts/haac.py task-run -- -n up`
- `python scripts/haac.py task-run -- up`
- `node scripts/verify-public-auth.mjs`
- Playwright CLI against `https://home.${DOMAIN_NAME}`
