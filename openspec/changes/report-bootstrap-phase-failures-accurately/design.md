## Design

The failure-summary path in `scripts/haac.py` already watches streamed `task` output. The regression came from two gaps:

1. `UP_TASK_PHASES` only covered a subset of top-level task names, while the real output for `task up` includes namespaced nested tasks such as `internal:wait-for-argocd-sync`, `security:post-install`, and `chaos:post-install`.
2. the phase collector accepted later lower-rank phases, so repeated preflight checks inside post-install work could overwrite a later GitOps phase.

The fix remains local to the wrapper:

- expand `UP_TASK_PHASES` with the task names actually emitted during the nested `up` graph
- define a stable phase order and ignore backward transitions when building the observed phase ladder
- parse explicit `[recovery]` lines first so lower-level helpers can override generic inference when they already know the exact failing phase

This keeps the runner thin and avoids teaching the wrapper about individual command strings beyond the existing `run-tofu` fallback.
