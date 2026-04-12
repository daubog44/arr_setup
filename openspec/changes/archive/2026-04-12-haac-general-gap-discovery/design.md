## Summary

The change expands discovery from “fix the loop if the loop is broken” to “find real HaaC gaps anywhere in the stack and convert them into narrow OpenSpec changes with a concrete first solution.” The implementation stays policy-driven: docs, skills, and prompt contract are updated so the runner behavior becomes broader without making the runner itself heavy.

## Design

### Discovery Scope

Discovery will explicitly allow evidence-backed gaps in:

- OpenTofu / infra topology
- Ansible / K3s bootstrap
- GitOps ordering, health, and namespace separation
- storage, GPU, networking, and device/plugin integration
- Cloudflare, ingress, auth, and public endpoint behavior
- Windows/Linux operator parity
- DRY, centralization, and generated source-of-truth drift
- missing post-setup, validation, or review automation

### Solution Proposal Requirement

Every discovered gap must include:

- problem statement
- evidence
- impact
- proposed minimal solution shape
- reason that the proposed solution is the right first move

This keeps discovery useful for implementation instead of generating vague backlog debt.

When the missing capability is in the model/operator layer, the proposed solution should prefer:

- local prompt or docs updates
- repo-local skills
- role prompts in `openspec/agents/`
- subagent policy
- `.codex` hook/bootstrap wiring
- runner bootstrap changes

instead of burying the missing behavior in unrelated product files.

### Runner Impact

The runner does not need new modes. `task loop:yolo` remains apply-first with discovery fallback, and discovery becomes broader by policy.
