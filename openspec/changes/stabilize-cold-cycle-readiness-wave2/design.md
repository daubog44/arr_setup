## Design

### Scope boundary

This wave is limited to the blockers proven by the real cold-cycle acceptance run. It does not broaden the media stack or add new public apps.

### Residual failure chain

The current cold-cycle failure chain is:

1. `task down` destroys the cluster, but some included Taskfiles still derive `MASTER_IP` from a stale or loopback-friendly fallback
2. CrowdSec LAPI data persists across the cold cycle, so recreated `agent` and `appsec` pods may try to register machine names that already exist
3. `wait-for-argocd-sync` reaches the child application phase and stalls on `crowdsec` because the app never becomes healthy
4. even when the rest of the stack is healthy, the Grafana browser verifier can still fail on a brittle text assertion that is not equivalent to a real dashboard error

### Taskfile contract

Every repo-supported Taskfile include must use the same `scripts/haac.py master-ip` resolver. The cold-cycle-safe logic should not live only in `Taskfile.yml` and `Taskfile.internal.yml`.

### CrowdSec recovery model

The repo-managed CrowdSec chart should follow the official Kubernetes guidance:

- set `api.client.unregister_on_exit: true`
- enable `api.server.auto_registration`
- restrict `allowed_ranges` to the actual pod CIDR surface
- enable agent or bouncer auto-delete windows in the local DB config

Because persisted local-path state can still contain stale machine rows immediately after a destructive cycle, the operator also needs a narrow runtime recovery:

- inspect CrowdSec machine registrations from the live LAPI
- detect machine IDs that map to current `agent` or `appsec` pods which are not ready and whose last heartbeat is stale
- delete only those stale machine rows
- delete the matching failing pods so they can re-register cleanly

This recovery belongs in the staged readiness path because `security:post-install` runs only after the staged ArgoCD gates succeed.

### Browser verification model

The Grafana verifier should keep failing on:

- missing datasource
- query/API/render errors
- `No data` when the dashboard is expected to have data

It should stop depending on one exact visible panel label on the Kubernetes API server dashboard, because that label is not stable across dashboard revisions and themes. The UID, route, and error-free dashboard shell remain the source of truth for the browser gate.

### Verification

- `openspec validate stabilize-cold-cycle-readiness-wave2`
- `python scripts/haac.py check-env`
- `python scripts/haac.py doctor`
- `python -m py_compile scripts/haac.py tests/test_haac.py`
- targeted unit coverage for Taskfile wiring, CrowdSec recovery logic, and the verifier contract
- `helm template haac-stack k8s/charts/haac-stack`
- `kubectl kustomize k8s/platform`
- `python scripts/haac.py task-run -- wait-for-argocd-sync`
- `node scripts/verify-public-auth.mjs`
- real `python scripts/haac.py task-run -- down`
- real `python scripts/haac.py task-run -- up`

### Recovery and rollback

- rollback removes the new CrowdSec runtime cleanup and restores the previous chart values, but that knowingly reintroduces the cold-cycle stall
- if the destructive cycle exposes another blocker, the active acceptance change must record it and either fix it directly when narrow or open one new evidence-backed change
