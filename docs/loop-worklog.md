# HaaC Loop Worklog

Worklog is a short operational diary for autonomous rounds.

Real files live in:

- `docs/worklogs/YYYY-MM-DD/HHMM-slug.md`

## Each Entry Must Say

- timestamp
- active change or discovery mode
- main files or systems touched
- validation command or review performed, including `python scripts/haac.py check-env` separately from `doctor` when live bootstrap reachability is part of the round
- finding, blocker, or decision
- next step

## Do Not Log

- every tiny edit
- full diff dumps
- repeated narration without a new finding

## Mandatory On Closeout

- exact validation commands run
- if `task up` did not complete, whether `check-env`, `doctor`, or a later phase was the blocker
- if `task up` did not complete, the furthest successful phase
- if a new change was opened, the change name and reason
