# Why

`task up` now reaches a usable end state, but it still carries avoidable blast-radius and convergence debt:

- `PUSH_ALL=true` can auto-commit and auto-push unrelated local work.
- bootstrap failures can leak secret values through command logging.
- SSH trust is effectively disabled across Python, Ansible, and generated inventory.
- ArgoCD bootstrap ownership is split between remote Ansible installs and local GitOps reconciliation.
- `litmus` and `node-problem-detector` remain out of sync after a successful bootstrap.
- `scripts/haac.py` is carrying too many high-risk concerns in one file.
- Authelia admin password is only implicit via a hash, not an explicit operator input.

The next outcome is not “more automation”. It is a safer, clearer, still-automatic bootstrap path that converges cleanly.

# What Changes

- Make `PUSH_ALL` safe-by-default and confine default publication to generated GitOps artifacts.
- Redact secrets from failure output and move SSH host verification from `no` to a managed `accept-new` model.
- Make the repo bootstrap ArgoCD from the local vendored source of truth, then hand off to self-management.
- Fix `node-problem-detector` and `litmus` so the platform converges after bootstrap.
- Add explicit `AUTHELIA_ADMIN_PASSWORD` support in `.env` and derive the file-backend hash automatically.
- Split reusable high-risk helper surfaces from `scripts/haac.py` into focused modules.

# Expected Outcome

- `task up` keeps working end to end.
- Default Git publication only touches generated GitOps outputs.
- Failed bootstrap logs no longer echo secret material.
- SSH trust is no longer disabled on every hop.
- ArgoCD bootstrap ownership is clearer and local to the repo.
- Argo shows clean convergence for `node-problem-detector` and `litmus`.
- Authelia admin password is an explicit operator input.
