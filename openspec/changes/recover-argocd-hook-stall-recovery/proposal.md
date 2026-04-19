## Why

Live validation on April 19, 2026 exposed a GitOps recovery gap that is distinct from the stale-revision case already covered in the repo.

- `kube-prometheus-stack` stayed `OutOfSync` with `status.operationState.phase=Running`
- ArgoCD kept reporting `waiting for completion of hook batch/Job/kube-prometheus-stack-admission-create`
- the referenced hook Job did not exist in the cluster anymore
- `scripts/haac.py` only auto-heals stale operations when the active revision differs from the desired revision, so this same-revision hook stall was not recovered automatically
- the stuck application delayed Bazarr and Unpackerr Prometheus targets until the child Application was manually recycled from the parent GitOps surface

That means `task up` can still leave a repo-managed child application blocked on a missing hook resource even when the desired revision is already current.

## What Changes

- Detect same-revision ArgoCD operations that are stuck waiting on missing hook resources.
- Add a safe recovery path for repo-managed child applications so the operator can recycle the child Application from its parent GitOps surface instead of requiring manual intervention.
- Extend GitOps readiness reporting so the operator output distinguishes ordinary sync lag from hook-stall recovery.

## Capabilities

### New Capabilities
- `argocd-hook-stall-recovery`: Recover repo-managed child Applications that stay stuck on missing hook resources at the current desired revision.

### Modified Capabilities
- `task-up-idempotence`: The supported rerun path must recover same-revision ArgoCD hook stalls instead of requiring manual child-Application deletion.

## Impact

- Affected code will primarily live in [scripts/haac.py](C:/Users/Utente/OneDrive%20-%20ITS%20Tech%20Talent%20Factory/Desktop/dev/arr_setup-main/scripts/haac.py), [tests/test_haac.py](C:/Users/Utente/OneDrive%20-%20ITS%20Tech%20Talent%20Factory/Desktop/dev/arr_setup-main/tests/test_haac.py), and the GitOps readiness docs.
- Verification must include OpenSpec validation, focused unit coverage for same-revision hook stalls, and a live rerun against the current ArgoCD surface when the environment is available.
