## Why

This repo needs a durable autonomous implementation loop that works from the official OpenSpec CLI instead of ad-hoc prompts and one-off sessions. The loop must be able to apply active changes, validate bootstrap work, review risky diffs, and open new evidence-backed changes when the repo or the loop itself is missing a capability.

## What Changes

- Add a CodexPotter-backed Ralph loop bootstrap for this repo with cross-platform task entrypoints.
- Add loop docs, local skills, worklog policy, and sidecar role prompts aligned with the homelab domain instead of the reference UI project.
- Add a loop readiness checker and dynamic prompt renderer that bind the loop to active OpenSpec changes, `task up`, and the repo validation ladder.
- Add explicit self-improvement rules so the loop can create one new evidence-backed OpenSpec change when it discovers missing bootstrap, validation, review, or skill coverage.

## Capabilities

### New Capabilities
- `autonomous-loop-runner`: the repo provides a supported loop runner that applies active OpenSpec changes through CodexPotter with deterministic bootstrap, docs, and task entrypoints
- `loop-self-improvement`: the loop can detect a missing capability in the repo or in its own bootstrap and create exactly one evidence-backed OpenSpec change

### Modified Capabilities
- `task-up-bootstrap`: the repo bootstrap contract now includes a persistent autonomous loop that validates and reviews `task up` work

## Impact

- `Taskfile.yml`
- `AGENTS.md`
- `README.md`
- `.gitignore`
- `.codex/`
- `docs/`
- `openspec/`
- `scripts/`
