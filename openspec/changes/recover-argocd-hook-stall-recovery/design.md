## Context

The current ArgoCD recovery logic already handles one class of stale operation:

- `status.operationState.phase=Running`
- `app.operation.sync.revision != status.sync.revision`

That does not cover the hook-stall case observed live on April 19, 2026:

- desired revision already current
- application message still waits on a hook job that no longer exists
- removing `/operation` and issuing a hard refresh was insufficient
- recycling the child `Application` through the parent GitOps application allowed the missing ServiceMonitors to be recreated and Prometheus scraping to converge

## Goals / Non-Goals

**Goals**

- Detect the missing-hook stall shape without relying on a revision mismatch.
- Recover only repo-managed child Applications, not arbitrary third-party or user-managed apps.
- Keep the operator rerun path idempotent and explicit about the recovery it performed.

**Non-Goals**

- This change does not redesign ArgoCD hook semantics globally.
- This change does not suppress hook execution for charts that legitimately need admission jobs.

## Decisions

### 1. Treat a missing-hook wait as a distinct recovery class

The recovery signal is:

- `status.operationState.phase == "Running"`
- the operation message matches `waiting for completion of hook ...`
- the referenced hook resource is not present anymore
- the application is repo-managed under the current GitOps repository URL

### 2. Recover via child-Application recycle when the app is GitOps-owned

For repo-managed child Applications, the minimal safe recovery is:

1. hard-refresh the parent/root Application surface if needed
2. delete the stuck child `Application` object only when it has no resource finalizer
3. let the parent GitOps application recreate it from repo state
4. re-evaluate sync and health

This matches the live recovery that restored `kube-prometheus-stack` scraping without mutating monitored resources directly.

### 3. Report the recovery explicitly

If the operator performs this recovery, it should emit a `[heal]` message that names the application and the missing hook resource it recovered from.

## Risks / Trade-offs

- Deleting an `Application` object is stronger than clearing `/operation`. Limiting this to repo-managed child apps without a resource finalizer keeps the blast radius bounded.
- Some charts may transiently recreate hook jobs slowly. The detector must only trigger after confirming the hook resource is absent, not merely pending.
