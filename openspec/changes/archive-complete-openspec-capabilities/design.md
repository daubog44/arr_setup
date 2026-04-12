## Context

The repo already has accepted change artifacts for bootstrap, loop execution, and general discovery, but they are stranded in completed change folders:

- `openspec list --json` shows only completed changes and no active work.
- `openspec/specs/` is empty, so there is no stable baseline for future spec deltas.
- `README.md` still says `openspec/changes/task-up-e2e-urls/` is the active bootstrap change even though the CLI reports it complete.

AGENTS.md defines `openspec/specs/<capability>/` as the stable source after archive or sync, so the current state is process debt, not just cosmetic drift.

## Goals / Non-Goals

**Goals:**
- Establish a stable `openspec/specs/` baseline from the completed changes
- Move completed changes out of the active change area without losing history
- Remove doc and prompt references that still treat completed changes as active
- Make future loop closeout more deterministic

**Non-Goals:**
- Redesign the accepted `task up` or loop requirements
- Add new operator-facing bootstrap behavior
- Introduce a new OpenSpec workflow schema or external tooling

## Decisions

1. Sync stable specs before archive.
   The accepted requirements already live in the completed change delta specs, so the first move is to copy or merge them into `openspec/specs/` before archiving. Alternative considered: archive first and leave stable specs empty. Rejected because it preserves the same missing-baseline problem.

2. Preserve full change history under `openspec/changes/archive/`.
   Completed changes should move to dated archive paths instead of being deleted so future operators can still inspect proposal, design, and task history. Alternative considered: leave completed changes in place. Rejected because it blurs active versus historical state and keeps docs more likely to drift.

3. Update repo references in the same implementation chunk.
   Docs that currently name completed changes as active should change alongside archive/sync work so the repo has one consistent story. Alternative considered: defer doc cleanup. Rejected because it would knowingly preserve stale operator guidance.

## Risks / Trade-offs

- Archive path churn may break hardcoded links -> Mitigation: update any direct references during the same change and prefer stable spec references where possible.
- The two completed changes that both touch loop self-improvement may need a careful merge -> Mitigation: treat stable spec sync as a deliberate review step, preserving history in the archived deltas.
- This change adds process work rather than product behavior -> Mitigation: keep the scope narrow and tie every step to future loop correctness and spec clarity.
