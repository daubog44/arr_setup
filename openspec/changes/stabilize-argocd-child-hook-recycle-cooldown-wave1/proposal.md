## Why

The cold-cycle validation for the Cobra migration exposed a real bootstrap bug in the GitOps readiness gate.

Concrete evidence from the live `.\haac.ps1 up` run on 2026-04-22:

- the stack converged far enough to create the cluster, run Ansible, publish GitOps, and begin ArgoCD staged readiness;
- `wait-for-stack` recycled the `kyverno` child Application after a missing hook;
- the same recovery path retriggered too aggressively and the run failed with `Timeout waiting for ArgoCD application kyverno recreation`;
- rerunning `task wait-for-argocd-sync` immediately afterwards succeeded, proving the child could converge once the recovery loop stopped thrashing it.

This matters because a cold `up` must not fail only because the hook-recovery logic re-deletes the same child application before the parent sync has time to restage it.

## What Changes

- add a short in-process cooldown around ArgoCD child-application hook recycling so the same child is not re-deleted immediately after a safe recycle;
- cover the cooldown with unit tests;
- rerun the cold-cycle `down` then `up` acceptance path to prove `kyverno` no longer stalls in the recovery loop.

## Capabilities

### Modified Capabilities

- `task-up-bootstrap`: the staged GitOps readiness gate must recover repo-managed child Applications with missing hooks without livelocking them during cold bootstrap.

## Impact

- Affected area: [scripts/haac.py](C:\Users\Utente\OneDrive - ITS Tech Talent Factory\Desktop\dev\arr_setup-main\scripts\haac.py) and [tests/test_haac.py](C:\Users\Utente\OneDrive - ITS Tech Talent Factory\Desktop\dev\arr_setup-main\tests\test_haac.py)
- Validation must include the live wrapper path because the bug only reproduced during a real cold-cycle `up`
