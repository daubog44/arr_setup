## Context

The runtime already enforces `python scripts/haac.py check-env` inside ordered `preflight`, and the current `task-up-idempotent-bootstrap` acceptance task keeps failing there before any remote mutation because the effective Proxmox access host is unresolved from the workstation. The loop review contract, however, still starts its ladder with `doctor`, which validates tool installation but not the live workstation-to-Proxmox path that determines whether `task up` can actually begin.

This gap lives in loop-facing docs and skills, not in product code. The smallest correct fix is to align the repo-local review guidance with the bootstrap contract that already exists in `README.md`, `docs/runbooks/task-up.md`, and `scripts/haac.py`.

## Goals / Non-Goals

**Goals:**

- Make `check-env` an explicit required validation gate for bootstrap-affecting review rounds.
- Distinguish toolchain readiness (`doctor`) from environment reachability (`check-env`) in loop docs and skills.
- Ensure worklog guidance records `check-env` results when live bootstrap attempts stop before sync or provisioning.

**Non-Goals:**

- Change the `task up` runtime behavior or bootstrap phase order.
- Add new environment variables or broader Proxmox connectivity features.
- Replace the existing full validation ladder for rounds that do reach later phases.

## Decisions

1. Update the loop review contract instead of bootstrap code.
   The runtime already blocks correctly in `check-env`. The missing capability is that the loop review ladder can under-report this gate, so docs and skill guidance are the right fix layer.

2. Place `check-env` before `doctor` in the ladder for bootstrap-affecting work.
   `check-env` validates the effective Proxmox access host and `.env` completeness for live bootstrap, while `doctor` focuses on workstation tool availability. Ordering the gates this way matches the actual bootstrap preflight and makes blockers easier to classify.

3. Align worklog and prompt guidance with the same distinction.
   If a round cannot reach live `task up`, the worklog should still show whether the failure was `check-env`, `doctor`, or a later phase. Keeping that terminology consistent avoids ambiguous "doctor passed but bootstrap was blocked" summaries.

## Risks / Trade-offs

- [Slightly longer validation ladder] -> Limit the new requirement to bootstrap-affecting rounds where live environment reachability matters.
- [Docs/skill drift if only one surface changes] -> Update `docs/loop-review.md`, `docs/haac-loop-prompt.md`, `docs/loop-worklog.md`, and `.codex/skills/haac-loop-review/SKILL.md` together.
- [Confusion about whether `check-env` replaces `doctor`] -> Keep both gates and document that they validate different surfaces.
