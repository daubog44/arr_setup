## Why

Litmus is now operator-free for environment and infrastructure enrollment, but it still lands with no repo-managed chaos scenarios tailored to this homelab.

The current bootstrap path already proves that:

- the canonical `haac-default` Litmus environment can be reconciled automatically
- the default chaos infrastructure can be registered without manual YAML download/apply
- the UI is considered broken if it still sends the operator through the legacy manual bootstrap path

What is still missing is a post-install seed step that gives the user a small, safe catalog of chaos workflows suitable for this stack.

## What Changes

- Add a repo-managed Litmus post-install catalog under source control.
- Extend the existing Litmus reconcile flow so it seeds a small set of homelab-safe workflow templates into ChaosCenter after the default infrastructure is active.
- Apply the minimum upstream Litmus experiment manifests needed for those templates so the saved workflows are runnable later without manual chart downloads.

## Capabilities

### Modified Capabilities

- `litmus-chaos-bootstrap`

## Impact

- Affected code lives in `scripts/haac.py`, `tests/test_haac.py`, `Taskfile.yml`, and `Taskfile.internal.yml`.
- New repo-managed artifacts live under `k8s/platform/chaos/`.
- Verification must include both cluster-side reconciliation and browser-level Litmus login plus template visibility.
