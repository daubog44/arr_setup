## Why

The autonomous loop can already improve itself, but the HaaC needs broader evidence-based discovery across the full homelab stack. Real gaps may live in infrastructure, GitOps, security, storage, cross-platform tooling, or post-setup automation, and the loop should be able to convert those findings into concrete OpenSpec changes with a proposed solution.

## What Changes

- Extend discovery policy so it explicitly covers the full HaaC, not only the loop runner.
- Require every discovered HaaC gap to include a proposed minimal solution shape.
- Align the loop prompt, docs, and discovery skill with this broader HaaC discovery contract.

## Capabilities

### New Capabilities
- `haac-gap-discovery`: the loop can identify real evidence-backed HaaC gaps across the stack and open an OpenSpec change that includes a proposed solution

### Modified Capabilities
- `loop-self-improvement`: loop discovery now covers both loop gaps and broader HaaC gaps, with explicit solution proposals

## Impact

- `AGENTS.md`
- `README.md`
- `docs/haac-loop-prompt.md`
- `docs/loop-discovery.md`
- `.codex/skills/haac-spec-discovery/SKILL.md`
- `openspec/changes/`
