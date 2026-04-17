## Context

`generate_secrets_core()` already owns the full set of sealed outputs written into the repo. The publication path does not reuse that ownership cleanly today:

- `push-changes()` stages `SECRETS_DIR`, `values.yaml`, and `GITOPS_RENDERED_OUTPUTS`
- `pre_commit_hook()` duplicates the same subset with a raw `git add`
- generated platform secrets outside `SECRETS_DIR` are therefore easy to regenerate but easy to forget during publication

The live Litmus decrypt failure proved this is not theoretical.

## Goals / Non-Goals

**Goals:**

- Make the staging list for generated GitOps artifacts explicit and shared.
- Ensure publication and pre-commit use the same repo-managed staging contract.
- Add regression coverage for the missing-path class of bug.

**Non-Goals:**

- Redesign GitOps publication or Git branching behavior.
- Solve every stale-cert scenario in this wave.
- Expand publication to all local work; only repo-managed generated artifacts are in scope.

## Decisions

### Centralize generated GitOps artifact paths

Introduce a single tuple/list derived from the known generated outputs (`values.yaml`, rendered manifests, platform SealedSecrets) and stage from that helper everywhere. This removes duplicated partial lists.

### Keep `SECRETS_DIR` staged as a directory

The chart secret outputs already live together and staging the directory is simpler than enumerating every file individually. The shared helper can add the extra generated files outside that tree.

### Cover the contract with a focused test

The highest-value regression here is confirming the shared stage list includes both platform-level secret outputs. That catches the exact class of omission that broke Litmus.

## Risks / Trade-offs

- [Risk] New generated outputs can still be missed if future code writes files without registering them in the shared list.  
  [Mitigation] The helper makes the omission surface smaller and easier to review than duplicated ad hoc staging calls.
- [Risk] This wave does not fix stale platform resources already published to Git.  
  [Mitigation] The live validation path reruns publication after the fix and verifies ArgoCD convergence.
