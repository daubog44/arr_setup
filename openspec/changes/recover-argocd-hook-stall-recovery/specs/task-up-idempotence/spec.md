## MODIFIED Requirements

### Requirement: Reruns recover partial GitOps publication failures

The supported rerun path MUST recover repo-managed ArgoCD child Applications that are stuck on same-revision missing-hook waits.

#### Scenario: Repo-managed child Application waits on a missing hook

- **WHEN** `task up` or a supported readiness rerun encounters a repo-managed child Application whose operation is waiting for completion of a hook resource that no longer exists
- **THEN** the operator MUST perform the supported hook-stall recovery path
- **AND** it MUST continue evaluating readiness from the recreated child Application instead of requiring manual deletion
