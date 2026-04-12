---
name: haac-loop-review
description: Run the HaaC validation and review ladder before closing bootstrap or loop work.
---

# HaaC Loop Review

Read `docs/loop-review.md` first.

Use this skill when:

- a change touches `task up`
- a change touches `Taskfile.yml`, `scripts/haac.py`, `scripts/haac_loop.py`, `.env`, `.ssh`, Cloudflare, secrets, `ansible/`, `tofu/`, or `k8s/`

Required behavior:

- run the validation ladder in order when applicable
- treat `python scripts/haac.py check-env` as a distinct live-environment gate before `doctor`, dry-run, or live `task up` conclusions
- call out skipped steps explicitly
- request architecture and security review sidecars for risky work
- if the round emits public URLs and Playwright MCP is available, require explicit browser navigation checks
- do not declare success without reporting the furthest verified phase
