## 1. Publication and Trust Boundaries

- [x] 1.1 Make `PUSH_ALL=false` the default safe path in task/env defaults and stop auto-checkpointing unrelated work when that mode is active
- [x] 1.2 Redact secret values from command failures and bootstrap diagnostics
- [x] 1.3 Replace always-off SSH trust with a repo-managed `known_hosts` plus `StrictHostKeyChecking=accept-new` model

## 2. Bootstrap Ownership and Convergence

- [x] 2.1 Move ArgoCD bootstrap ownership out of the remote Ansible URL install path and into the repo-local Python bootstrap path
- [x] 2.2 Fix `node-problem-detector` convergence by removing the duplicate `NODE_NAME` override
- [x] 2.3 Fix `litmus` convergence by switching the MongoDB topology to a homelab-appropriate single-node setup

## 3. Source Of Truth and Structure

- [x] 3.1 Add explicit `AUTHELIA_ADMIN_PASSWORD` support and derive the hash automatically during hydration
- [x] 3.2 Extract high-risk reusable helper surfaces from `scripts/haac.py` into focused modules
- [x] 3.3 Update docs to describe the new publication, bootstrap, cloudflared autoupdate, and Authelia password behavior

## 4. Validation

- [x] 4.1 Run `openspec validate harden-task-up-automation-boundaries`
- [x] 4.2 Run the HaaC validation ladder that applies here: `check-env`, `doctor`, `task -n up`, `py_compile`, `helm template`, `kubectl kustomize`, and a live `task up`
- [x] 4.3 Re-check Argo application sync state and emitted public URLs after the live bootstrap
