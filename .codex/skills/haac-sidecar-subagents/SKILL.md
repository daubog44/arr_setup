---
name: haac-sidecar-subagents
description: Use narrow sidecar subagents for architecture, security, validation, and docs review inside the HaaC loop.
---

# HaaC Sidecar Subagents

Read `docs/loop-subagents.md` first.

Use sidecars for:

- architecture review
- security review
- validation triage
- documentation drift

Rules:

- main agent keeps ownership
- prompts must be exact and bounded
- treat sidecar output as evidence, not authority
