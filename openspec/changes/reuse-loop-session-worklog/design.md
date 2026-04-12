## Context

The runner currently names worklogs as `docs/worklogs/YYYY-MM-DD/HHMM-<slug>.md` inside `ensure_worklog()`. That means the only reuse path is hitting the exact same minute twice. The repo already shows the resulting fragmentation for `task-up` on `2026-04-12`, where the worklog directory contains many same-day files such as `0113-task-up.md`, `0114-task-up.md`, `0238-task-up.md`, and `1510-task-up.md`.

An isolated reproduction confirms the behavior: with an existing `2026-04-12/1510-task-up.md`, calling `ensure_worklog("task-up", "discover", [])` at a later timestamp still creates `2026-04-12/1615-task-up.md` instead of reusing the existing session file.

## Goals / Non-Goals

**Goals:**
- Keep one deterministic current session worklog per same-day slug
- Make `run`, `prompt`, and `worklog` agree on the worklog path they use
- Preserve the current file naming shape for first-time worklog creation

**Non-Goals:**
- Redesign the worklog file format
- Rewrite or merge historical duplicate worklogs
- Add external session-state storage outside the existing runner surfaces

## Decisions

1. Reuse the most recent same-day worklog that matches the requested slug before creating a new file.
   This is the narrowest fix because it uses the existing worklog directory as the source of truth and does not require new state files. Alternative considered: persist the current worklog path in extra loop state. Rejected because the repo already has the needed signal in the worklog directory itself.

2. Keep minute-stamped filenames for first creation.
   The first worklog for a slug on a given day should still use the existing `HHMM-slug.md` pattern so the repo does not churn its worklog naming convention. Alternative considered: switch to one fixed `slug.md` file per day. Rejected because it would be a broader change to established file naming.

3. Reuse the existing header synchronization path after worklog selection.
   Once the runner picks the worklog path, it should continue updating only the generated `mode` and `active_changes` header lines. Alternative considered: special-case reused files. Rejected because it duplicates the same header contract in multiple branches.

## Risks / Trade-offs

- Same-day intentionally separate sessions that reuse the same slug will append to the same file. -> Mitigation: this is already the repo's dominant operational pattern for `task-up`, and separate sessions can still use a different slug when strict isolation matters.
- Historical fragmented worklogs remain on disk. -> Mitigation: keep this change forward-looking and avoid risky diary rewrites.
- Selecting the wrong prior file would misdirect the prompt. -> Mitigation: limit reuse to same-day files whose basename ends with the normalized slug and choose the most recently modified match.
