# ephemeral-wsl-ssh-and-artifact-hygiene

## Why

The Windows operator path no longer copies the bootstrap SSH key into `~/.ssh` inside WSL, but that improvement is not yet captured in an active OpenSpec change and the repo still contains scratch artifacts outside `.tmp/`.

That leaves two gaps:

- the WSL runtime hygiene change is not traceable through the official OpenSpec workflow
- operator-created investigation artifacts can still accumulate in the repo root instead of a single ignored runtime area

## What Changes

- formalize the ephemeral WSL SSH runtime path under `.tmp/`
- keep `known_hosts` repo-managed, but treat the WSL copy as runtime-only
- add an explicit repo cleanup path for stray investigation artifacts outside `.tmp/`
- document in `AGENTS.md` that future temporary artifacts belong under `.tmp/`

## Acceptance Criteria

- Windows `run-ansible` uses a per-run WSL runtime directory under `.tmp/` and cleans it up on exit
- no persistent `~/.ssh/haac_ed25519` copy is required in WSL
- `AGENTS.md` explicitly states that operator-created scratch artifacts must live under `.tmp/`
- the repo root is cleaned of stray logs/screenshots/dumps created during prior investigation outside `.tmp/`
- static validation passes for the bootstrap path after the hygiene changes
