## Why

The live `task down -> task up` acceptance wave exposed three residual blockers that still prevent the cold-cycle contract from closing cleanly:

- included Taskfiles (`security`, `media`, `chaos`) still resolve `MASTER_IP` through the old `tofu-output --default 127.0.0.1` path instead of the cold-cycle-safe resolver
- CrowdSec can remain `Synced Progressing` after a cold cycle because persisted LAPI machine registrations survive while the recreated `agent` and `appsec` pods try to register the same identities again and receive `403 user already exist`
- the browser-level Grafana verifier still depends on unstable panel text on the Kubernetes API server dashboard even when the dashboard shell and datasource are healthy

Those are real acceptance blockers, not cosmetic drift. The operator wants a full `down -> up -> verify` proof, so the repo needs one bounded stabilization wave that removes these residual gates.

## What Changes

- propagate the cold-cycle-safe `master-ip` resolver to every included Taskfile that still uses the stale loopback fallback
- align the repo-managed CrowdSec chart values with the official Kubernetes registration guidance and add a narrow runtime recovery for stale machine registrations after cold cycles
- keep the browser verifier strict on real Grafana errors while removing the brittle panel-text dependency on the Kubernetes API server dashboard
- validate the result by rerunning the staged ArgoCD gate, browser verification, and the real destructive acceptance cycle

## Capabilities

### Modified Capabilities
- `full-lifecycle-acceptance`: cold-cycle acceptance must survive included Taskfiles, CrowdSec runtime registration drift, and browser verification without manual cleanup

## Impact

- Affected code lives in `Taskfile.chaos.yml`, `Taskfile.media.yml`, `Taskfile.security.yml`, `scripts/haac.py`, `scripts/verify-public-auth.mjs`, `tests/test_haac.py`, and CrowdSec GitOps manifests.
- Validation must include OpenSpec, targeted tests, render gates, staged ArgoCD readiness, browser verification, and a real `task down` followed by `task up`.
