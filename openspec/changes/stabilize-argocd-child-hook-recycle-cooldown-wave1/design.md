## Design

### Failure shape

The existing recovery path is intentionally aggressive:

1. detect a repo-managed child Application waiting on a missing hook;
2. delete the child;
3. sync the parent;
4. wait for a new child UID.

That is safe once, but during a cold bootstrap the recreated child can still report the same hook-wait state before the parent sync has fully settled. The current logic then treats that transient state as a new stall and recycles the child again.

### Cooldown guard

The recovery path will track a short per-application recycle timestamp in process memory.

- After a successful recycle request, the application enters cooldown.
- While the cooldown is active, the recovery helper returns `False` for that application and lets the normal readiness loop continue observing health/sync progression.
- The cooldown only applies to the current `wait-for-stack` process; it does not create cluster-side state.

This preserves the existing recovery behavior for true missing-hook stalls while preventing self-inflicted thrash on the same child app.

### Validation

- targeted unit tests for the cooldown path
- `openspec validate stabilize-argocd-child-hook-recycle-cooldown-wave1`
- `python -m unittest` on the affected test slice
- live `.\haac.ps1 down`
- live `.\haac.ps1 up`
- `.\haac.ps1 task wait-for-argocd-sync`
- `.\haac.ps1 task verify-all`
