## Context

`task up` is intentionally publish-only on the Git boundary. When `origin/<revision>` moves ahead, the operator is supposed to run `task sync` first. The current sync implementation fetches, checkpoints local dirty state, and only then computes the relationship between `HEAD` and `origin/<revision>`. That order is fine when the remote is equal or behind, but it is wrong when the remote is already ahead and the worktree contains tracked generated outputs from a failed or partial publication round.

The live repo state that triggered this change was narrow and real:

- `origin/main` moved ahead by a single safe dependency update commit
- local tracked Sealed Secrets and other generated GitOps outputs were dirty
- `task up` correctly refused to publish while behind
- `task sync`, if run unchanged, would have created a local checkpoint commit first and then reported divergence

That is an operator-recovery bug, not a policy choice.

## Goals / Non-Goals

**Goals:**

- Keep merge policy explicit in `task sync`, not in `task up`.
- Allow `task sync` to fast-forward cleanly when the remote is ahead and local changes are only uncommitted worktree state.
- Preserve local dirty changes across that fast-forward and leave the repo in a publishable state afterward.
- Add regression coverage for the ref-state and dirty-worktree decision flow.

**Non-Goals:**

- Auto-merge divergent branches.
- Change `push-changes` into a merge-capable path.
- Solve every possible Git workflow conflict in the repo.

## Decisions

### Decide sync direction before checkpointing

`sync_repo()` will determine ref-state against `origin/<revision>` before creating any checkpoint commit. That prevents the explicit sync path from manufacturing divergence in a case that started as a simple fast-forward.

### Use an explicit stash/apply cycle for behind-plus-dirty recovery

When the remote is ahead and the worktree is dirty, sync will temporarily stash local worktree changes, fast-forward to the remote, re-apply the stash, and only then create the usual checkpoint commit if local changes remain. This keeps the merge policy explicit while preserving the operator's regenerated outputs.

Alternatives considered:

- Commit first, then fast-forward: rejected because it creates false divergence.
- Hard reset local changes: rejected because it loses operator-generated state.
- Move merge logic into `push-changes`: rejected because it violates the publish-only boundary.

### Fail closed on stash apply conflicts

If the re-apply step conflicts, sync will stop with an explicit recovery message instead of guessing. That keeps the safe case automatic without hiding real merge conflicts.

## Risks / Trade-offs

- [Risk] A stash/apply cycle is more complex than the current sync path.  
  Mitigation: keep it limited to the behind-plus-dirty case and cover it with tests.
- [Risk] Untracked local artifact noise can still pollute explicit sync.  
  Mitigation: keep the stash targeted to tracked worktree changes for this wave and address general repo hygiene in a separate cleanup change.
- [Risk] Operators may assume `task up` now auto-syncs.  
  Mitigation: docs and stable specs will continue to state that merge policy belongs only to `task sync`.
