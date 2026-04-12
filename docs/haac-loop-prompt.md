# HaaC Ralph Loop Prompt

## Global Priority

Main task of the loop is to move the homelab toward a reliable one-command bootstrap:

- `task up` or wrapper equivalent works
- the current architecture stays coherent
- the stack stays modern, DRY, centralized, and reviewable
- public URLs are emitted as part of the operator contract

Process artifacts support that goal. They do not replace it.

## Mandatory Read Order

At round start read:

1. `AGENTS.md`
2. `README.md`
3. `ARCHITECTURE.md`
4. `docs/runbooks/task-up.md`
5. `docs/loop-review.md`
6. `docs/loop-discovery.md`
7. `docs/loop-subagents.md`
8. `docs/loop-worklog.md`
9. the active OpenSpec change artifacts
10. the current session worklog

If a required file is missing, treat that as setup debt and fix it first.

## Operating Rules

- use the official OpenSpec CLI, not ad-hoc local conventions
- if one or more active changes exist, pick the first change with pending tasks and work that change first
- normal apply mode is apply-first with autodiscovery fallback, not apply-only
- one coherent OpenSpec task chunk per round, max
- one new evidence-backed OpenSpec change per round, max
- one coherent task chunk per round is preferred; do not spray unrelated repo edits
- validation, review, and security review are mandatory for bootstrap-affecting work
- when live bootstrap depends on workstation-to-Proxmox reachability, run and record `python scripts/haac.py check-env` before treating `doctor` or a blocked `task up` attempt as evidence of readiness
- if validation fails, default action is fix or document the blocker with evidence, not silent acceptance
- update docs and task checklists when behavior changes
- if a missing loop capability blocks correctness, open exactly one new evidence-backed OpenSpec change for that gap
- do not create speculative changes just to keep the loop busy
- if a round emits or verifies public URLs, use Playwright MCP to navigate them in a browser context after HTTP-level verification
- autodiscovery scope includes the whole HaaC stack, not only the loop bootstrap
- if you discover a real HaaC gap, propose a concrete minimal solution in the OpenSpec change, not only the problem
- if the missing capability lives in loop assets, you may create or refine local skills, prompt rules, role prompts, subagent policy, hook/bootstrap glue, or runner logic as the first-class fix
- if no active OpenSpec change remains, stop unless the same round already found one concrete new gap; if so, write exactly one new change and stop the round
- if nothing evidence-backed remains to implement or discover, CodexPotter itself must stop the rollout; do not keep rounds alive artificially
- if no active change exists at round start, discovery is a one-shot decision: either open exactly one evidence-backed change or end the rollout in that same round
- do not spend spare rounds rereading the repo when no active change exists and no new evidence-backed gap was found

## Auto-Improve Rule

The loop SHALL improve itself when it finds a real gap in:

- preflight
- validation
- review or security review
- OpenSpec scaffolding
- local skills
- runner bootstrap or isolated Codex home setup
- missing repo-local agent capability that should live in prompt, skill, agent role, hook, MCP wiring, or subagent policy

Evidence must include the missing contract, the failing command or blind spot, and the impact on `task up` or loop reliability.

This rule also applies during normal `task loop:yolo` runs. The loop does not need a separate discovery-only run to open one new evidence-backed change when the current round proves that a missing capability exists.

Valid HaaC discovery categories include:

- infrastructure provisioning or topology debt
- Ansible or K3s bootstrap debt
- GitOps ordering, health, or namespace contract gaps
- Cloudflare, DNS, auth, ingress, or public endpoint issues
- storage, GPU, networking, or device-plugin integration gaps
- DRY, centralization, or generated-source-of-truth drift
- Windows/Linux operator parity issues
- missing post-setup or verification automation

If Playwright MCP is available through the repo-local bootstrap, use it explicitly. Do not treat browser verification as optional or implied.

## Preferred Skills

If installed in the current Codex home, prefer these skills when relevant:

- `openspec-apply-change`
- `openspec-propose`
- `haac-loop-review`
- `haac-spec-discovery`
- `haac-sidecar-subagents`
- `caveman`

## Definition Of Done

Do not claim progress on bootstrap work unless the round intentionally handled:

- OpenSpec artifact alignment
- implementation
- validation from `docs/loop-review.md`
- worklog update
- explicit blocker classification when bootstrap stops before completion: `check-env`, `doctor`, or a later phase
- sidecar review when the touched area is risky enough to need it
- browser-level URL verification with Playwright MCP when the round reached public endpoint output

If nothing remains to implement or discover, emit a final completion note and end the run.

Stop round after the active task chunk is complete.
