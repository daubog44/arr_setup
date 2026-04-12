# HaaC Loop Discovery

Discovery exists to create or refine OpenSpec changes from evidence.

It applies to the whole HaaC, not only the loop itself.

It also applies to the loop assets themselves when the missing capability should live in local prompting or agent scaffolding rather than product code.

## Allowed Triggers

You may open a new OpenSpec change only when you have at least one of:

- a failed validation command in the bootstrap ladder
- a missing operator contract for `task up`
- a real architecture or security inconsistency in the current homelab stack
- a missing loop capability that blocks reliable autonomous work
- a gap between docs, specs, and actual repo behavior
- a real gap in infrastructure, GitOps, storage, security, networking, post-setup automation, Windows/Linux parity, or DRY/centralization
- a missing repo-local LLM capability that should be solved by loop prompt, docs, skills, agent roles, subagent policy, hooks, or MCP/bootstrap wiring

## Required Evidence

Before creating a new change, record:

- exact scope
- exact failure, mismatch, or missing capability
- one command output, file path, or concrete observation
- why this matters to `task up`, GitOps reliability, or loop correctness
- the proposed minimal solution shape
- why that proposed solution is the right first move

## Forbidden Triggers

- “the repo feels improvable”
- empty backlog with no evidence
- speculative modernization with no concrete contract gap
- duplicate changes for the same issue

## Auto-Improve Discovery

If the missing capability is in the loop itself:

- create one new change
- keep it narrow
- classify it as preflight, validation, review, bootstrap, or discovery debt
- prefer fixing the capability at the right layer: prompt, docs, local skill, role prompt, subagent policy, hook, runner bootstrap, or MCP wiring
- stop after writing the change unless the same round can safely finish the smallest required fix

## General HaaC Discovery

If the missing capability is in the broader homelab stack:

- classify it as infra, ansible, k8s, gitops, storage, security, networking, tooling, docs, or automation debt
- propose the narrowest solution that materially improves `task up`, operator reliability, or stack coherence
- prefer solutions that improve centralization and DRY instead of adding one-off exceptions
