---
name: haac-spec-discovery
description: Open one evidence-backed OpenSpec change when the repo or the loop itself is missing a required capability.
---

# HaaC Spec Discovery

Read `docs/loop-discovery.md` first.

Use this skill when:

- there is no active change and real evidence of missing work exists
- the loop detects a missing capability in preflight, validation, review, skills, or bootstrap
- a contract gap exists between docs, specs, and real behavior
- the broader HaaC has a real gap in infra, GitOps, security, storage, networking, DRY, cross-platform behavior, or automation
- the model is missing a repo-local capability that should live in prompt/docs/skills/agents/subagents/hooks/MCP bootstrap instead of application code

Rules:

- create at most one change per round
- keep the change narrow
- cite the evidence in proposal/design/tasks/specs
- include the proposed minimal solution shape and why it is the right first move
- when the gap is in model behavior, prefer adding or refining repo-local skills, prompt rules, agent roles, subagent policy, or hook/bootstrap config
- stop after creating the change unless the smallest safe follow-up is obvious and already in scope
- if no evidence-backed gap exists, stop the rollout in the same round instead of keeping discovery alive
