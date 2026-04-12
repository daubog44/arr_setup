## Summary

The repo will gain a thin, cross-platform Ralph loop runner that wraps CodexPotter and the official OpenSpec CLI. The loop runner will not re-implement operator logic already present in `scripts/haac.py`; it will reuse those commands for readiness checks and validation while moving policy into docs, local skills, and OpenSpec role prompts.

## Architecture

### Runner

Add `scripts/haac_loop.py` as the loop entrypoint with four responsibilities:

1. run local readiness checks and validate active OpenSpec changes
2. prepare an isolated repo-local `CODEX_HOME` when not using the global one
3. create a dated worklog path
4. render a dynamic prompt and pass it to `codex-potter exec`

### Prompt and Policy

Move loop policy into docs:

- `docs/haac-loop-prompt.md`
- `docs/loop-review.md`
- `docs/loop-discovery.md`
- `docs/loop-subagents.md`
- `docs/loop-worklog.md`

This keeps the runner thin and the behavioral contract inspectable.

### Skills and Agent Roles

Add repo-local skills for:

- review/validation
- spec discovery
- sidecar subagent usage

Add `openspec/agents/*.md` so sidecar roles remain stable and repo-specific.

### Self-Improvement

The runner will expose both apply and discovery modes. The prompt will require:

- apply the first active change with pending tasks when active changes exist
- otherwise perform narrow discovery
- when a missing loop capability is discovered, open exactly one new OpenSpec change with evidence

## Validation

The loop readiness checker will require:

- required docs and local skills present
- `codex`, `codex-potter`, and `openspec` installed
- `python scripts/haac.py doctor` passes
- `openspec list --json` succeeds
- active changes validate with `openspec validate <change>`

For risky or bootstrap-affecting work, the loop policy will also require the repo validation ladder from `docs/loop-review.md`.
