## Context

The loop currently reasons only about active OpenSpec changes. That works for normal apply mode, but it leaves two forms of OpenSpec debt invisible:

- completed changes can remain under `openspec/changes/` without their accepted deltas merged into `openspec/specs/`
- scaffold-only change directories can remain behind after aborted `openspec new change ...` attempts and still appear in some CLI surfaces

Today that means `openspec list --json` can say there are no active changes while other CLI commands still expose incomplete or historical change state. The loop prompt then treats the repo as discovery-idle instead of surfacing the cleanup debt explicitly.

## Goals / Non-Goals

**Goals:**

- Make the loop runner report completed-change closeout debt and scaffold-only change debt when it prepares a session.
- Keep the change surface consistent by archiving the current completed changes and removing orphan scaffolds.
- Preserve the existing apply-versus-discovery behavior for real active changes.

**Non-Goals:**

- Build a fully automatic archival daemon that archives every completed change during command execution.
- Redesign the broader OpenSpec workflow or add new external dependencies.
- Reopen or implement the abandoned K3s CNI changes; this change only cleans invalid scaffolds.

## Decisions

1. Report hygiene debt in the runner and prompt, not only in docs.
   The missing capability is operational: the loop needs concrete session context when the OpenSpec tree is dirty. Updating only docs would leave `check`, `prompt`, and `run` blind to the actual repo state.

2. Treat scaffold-only change directories as hygiene debt.
   `openspec status --change ... --json` proves that a directory containing only `.openspec.yaml` is still visible to the CLI even though it never became a usable change. Removing those stubs is the narrowest way to restore a consistent change surface.

3. Use the official `openspec archive` command for completed changes.
   Stable spec sync and dated history paths are already defined by the repo contract. Reusing the CLI avoids ad-hoc archive logic and keeps the archive layout canonical.

## Risks / Trade-offs

- [Prompt noise] More session context can bloat discovery prompts. -> Mitigation: only include hygiene sections when debt exists.
- [Cleanup scope] Archiving several completed changes in one pass touches multiple specs. -> Mitigation: keep implementation narrow to already accepted completed changes and validate specs afterward.
- [False positives] A partially created change could be intentional work-in-progress. -> Mitigation: classify only directories whose tracked content is limited to `.openspec.yaml` as scaffold-only debt.

## Migration Plan

1. Add loop-runner support for identifying completed and scaffold-only changes and surfacing them in `check` and prompt rendering.
2. Add regression tests for the new session-context behavior.
3. Remove the scaffold-only change directories.
4. Archive the completed changes with the official CLI so the missing stable specs are created and the histories move under `openspec/changes/archive/`.
5. Validate the new change and the resulting stable specs, then update worklog and KB evidence.

## Open Questions

- None. The current repo state already provides the necessary evidence and the cleanup boundary is narrow.
