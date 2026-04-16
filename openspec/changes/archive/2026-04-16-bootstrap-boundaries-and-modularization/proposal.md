# bootstrap-boundaries-and-modularization

## Why

The repo already renders the Argo root applications from templates, but the main operator path still mixes bootstrap with Git merge policy. Today `task up` runs `sync` during preflight and `push-changes` can still merge remote state when `PUSH_ALL=true`.

That keeps two boundaries blurry:

- bootstrap versus Git merge policy
- orchestration versus low-level Git state logic inside `scripts/haac.py`

## What Changes

- keep Argo root applications explicitly template-driven from `.env`
- remove `sync` from the default `preflight` / `task up` happy path
- make `push-changes` a publication step only, not a remote merge policy step
- move Git state helpers out of `scripts/haac.py` into `scripts/haaclib/`

## Acceptance Criteria

- `task up` no longer runs `sync` as part of preflight
- `push-changes` never performs a merge; when the local branch is behind or diverged it fails with explicit guidance to run `task sync`
- Git state helper logic lives in `scripts/haaclib/` instead of the main orchestration file
- static validation passes for the bootstrap path after the refactor
