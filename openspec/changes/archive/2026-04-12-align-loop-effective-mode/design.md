## Context

`scripts/haac_loop.py` already computes an effective session mode in `run_loop()` by downgrading `apply` to `discover` when `openspec list --json` reports no active changes. That effective-mode decision does not flow through the standalone `cmd_prompt()` and `cmd_worklog()` entrypoints, and `ensure_worklog()` currently preserves any existing header without reconciling it with the selected session state.

The result is a split contract on the public CLI surface:

- `python scripts/haac_loop.py run --slug <slug> --mode apply --dry-run` emits a discovery-mode prompt when there are no active changes.
- `python scripts/haac_loop.py prompt --slug <slug> --mode apply` emits an apply-mode prompt for the same repo state.
- `python scripts/haac_loop.py worklog --slug <slug> --mode apply` creates a worklog stub with `- mode: apply` and `- active_changes: none`.

This is loop-runner correctness debt because the next agent or operator sees a different contract depending on which helper generated the session artifacts.

## Goals / Non-Goals

**Goals:**
- Resolve the effective session mode once and reuse it across `run`, `prompt`, and `worklog`
- Keep session worklog headers aligned with the effective mode and active change set used for the session
- Add a lightweight regression check for the no-active-change apply path

**Non-Goals:**
- Change how active changes are discovered or filtered
- Redesign the worklog format beyond the existing header fields
- Broaden discovery behavior beyond this session-artifact consistency fix

## Decisions

1. Route all session-artifact creation through one effective-mode decision.
   `run`, `prompt`, and `worklog` should all compute the same selected change set and the same effective mode before rendering prompts or worklogs. Alternative considered: patch only `cmd_prompt()` and `cmd_worklog()` call sites independently. Rejected because it keeps the session-state contract duplicated.

2. Reconcile existing worklog headers instead of only fixing newly created files.
   When a same-session worklog already exists, the runner should refresh the `mode` and `active_changes` header lines to the effective session state rather than returning the file untouched. Alternative considered: leave existing worklogs immutable. Rejected because the first helper invocation in a minute can still create a stale header that every later command reuses.

3. Validate through the public CLI surface.
   The regression evidence and acceptance check should use the existing `run --dry-run`, `prompt`, and `worklog` commands so the change protects operator-visible behavior, not only internal helpers. Alternative considered: rely on code inspection alone. Rejected because the defect already lived in the CLI glue rather than the mode helper itself.

## Risks / Trade-offs

- Header reconciliation could overwrite manual edits to the top-of-file mode metadata. -> Mitigation: limit updates to the generated header lines and leave later notes untouched.
- Historical worklogs created before the fix remain inconsistent. -> Mitigation: do not rewrite historical diaries; guarantee correctness for new or reused session artifacts after the fix lands.
- This change touches loop bootstrap behavior without changing end-user HaaC features. -> Mitigation: keep the implementation narrow and validate with the same commands operators and the loop use today.
