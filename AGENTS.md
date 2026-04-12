# AGENTS.md

## Project Objective

This repository exists to deliver a homelab-as-code workflow where one command boots the full stack:

1. OpenTofu provisions the required Proxmox LXC infrastructure.
2. Ansible configures Proxmox, mounts storage, and installs/configures K3s.
3. GitOps bootstraps ArgoCD and reconciles platform plus workloads.
4. Cloudflare Tunnel and DNS are reconciled automatically.
5. The final operator output includes the public URLs that are expected to be visitable.

The operator contract is:

- Windows: `.\haac.ps1 up`
- Linux/macOS: `sh ./haac.sh up`
- Global Task, if installed: `task up`

`task up` is the product. Everything else supports that path.

## Source Of Truth

- `.env` is the single source of truth for operator inputs, secrets, tool versions, infra flags, GitOps repo settings, and all Terraform-backed values.
- `.env` is sensitive. Never print it in full, never commit it, and never duplicate its values into code unless the target file is a generated artifact derived from templates.
- `WORKER_NODES_JSON` is the source of truth for worker topology. Preserve type safety in OpenTofu.
- Generated files must be derived from templates and `.env`, not edited as primary sources.

## Non-Negotiable Invariants

- No hardcoded infra values outside templates and generated outputs.
- `LXC_UNPRIVILEGED=true` remains the default model unless a spec explicitly proves otherwise.
- GPU workloads use standard Kubernetes resources such as `nvidia.com/gpu`; infra discovery should prefer NFD over custom scheduling labels.
- Windows and Linux are first-class operator environments. `.tools/<os>-<arch>/bin` is the portable CLI layer.
- The primary kubeconfig on the workstation must not be mutated as a side effect of a temporary tunnel session.
- GitOps health must be validated in phases, not inferred from one workload alone.
- `task up` must remain the primary supported rerun path after partial failure unless the failure output explicitly requires manual intervention.
- Bootstrap failures must report the failing phase, the last verified phase, and rerun guidance rather than leaving recovery implicit.

## OpenSpec Workflow

Non-trivial work must run through `openspec/`.

Structure:

- `openspec/changes/<change>/`: active official OpenSpec change proposals, designs, tasks, and delta specs
- `openspec/changes/archive/<date>-<change>/`: archived completed change history
- `openspec/specs/<capability>/`: stable capability specs after archive or sync
- `openspec/agents/`: stable role prompts for sidecar and meta-agent usage in this repo

Rules:

- One change = one observable outcome.
- Every active change MUST define scope, inputs, acceptance criteria, verification commands, expected outputs, and rollback or recovery notes.
- No broad repo changes without an active change under `openspec/changes/`.
- Use `openspec list --json` as the only source of truth for which changes are active.
- Stable capability contracts belong in `openspec/specs/` after archive; completed changes MUST not keep being described as active in repo docs.
- The autonomous implementation loop behavior is defined by the archived and stable OpenSpec artifacts, not by stale hardcoded change names in docs.

## Ralph Loop

This repo ships a CodexPotter-backed Ralph loop for long-running autonomous work on top of OpenSpec.

Supported entrypoints:

- `task loop:yolo SLUG=<slug> ROUNDS=<n>`
- `task loop:yolo:checked SLUG=<slug> ROUNDS=<n>`
- `task loop:discover SLUG=<slug> ROUNDS=<n>`

The loop contract is:

- read the repo/operator docs in the declared order
- apply the first active OpenSpec change with pending tasks
- run validation and review gates before declaring progress
- keep autodiscovery active even during normal `task loop:yolo` runs
- if the active change finishes, if no active change exists, or if the loop itself lacks a required capability, create exactly one evidence-backed OpenSpec change and stop or continue within the current round only if safe

Auto-improve is mandatory:

- if the loop discovers missing review coverage, missing preflight, missing validation, missing skill coverage, missing docs, or a bootstrap blind spot, it MUST open a new OpenSpec change for that loop capability instead of silently working around it
- discovery without evidence is forbidden; every new change needs a concrete mismatch, failure, or missing contract
- autodiscovery also applies to the broader HaaC stack, including infrastructure, GitOps topology, storage, security, cross-platform tooling, DRY violations, post-setup automation, and open-source integration mismatches
- every discovered HaaC gap must include a proposed solution shape, not only the problem statement
- loop auto-improve scope explicitly includes `scripts/haac_loop.py`, `docs/haac-loop-prompt.md`, `docs/loop-*.md`, repo-local skills under `.codex/skills/`, role prompts under `openspec/agents/`, hook/bootstrap files under `.codex/`, and MCP/bootstrap config when those are the missing capability surface
- if the LLM lacks an operational capability for this repo, the preferred first fix is to add or refine a local skill, prompt rule, agent role, subagent policy, or bootstrap hook before adding ad-hoc instructions elsewhere

## Agent Roles

- `meta-orchestrator`
  - owns sequencing, scope, and dependency management across specs
- `architect-reviewer`
  - reviews cross-layer consistency across `tofu/`, `ansible/`, `k8s/`, and `scripts/`
- `security-auditor`
  - reviews `.env`, `.ssh`, Sealed Secrets, Cloudflare, OIDC, and bootstrap trust boundaries
- `devops-pipeline`
  - owns `Taskfile.yml`, `scripts/haac.py`, `.tools/`, WSL bridging, and the reliability of `task up`
- `gitops-k8s`
  - owns ArgoCD topology, namespaces, sync waves, health gates, gateway routing, and cluster-side bootstrap
- `docs-maintainer`
  - keeps `README.md`, `ARCHITECTURE.md`, runbooks, and spec docs aligned with reality

## MCP And Skill Usage

Use the smallest set that materially improves correctness.

- GitHub MCP
  - use for remote branch state, PR/repo coordination, and remote source-of-truth checks
- Playwright skill
  - use for URL verification, browser-level endpoint checks, and screenshots when the spec requires public reachability validation
- Context7
  - use when available in the active client for up-to-date library or tool documentation
- Figma and n8n tools
  - use only when the spec explicitly touches design or workflow automation domains

If a configured MCP is not exposed in the current client session, note that explicitly and continue with the best local fallback.

If a round produces or verifies public service URLs, the loop MUST use Playwright MCP for browser-level navigability checks in addition to HTTP-level verification when the MCP is available.
The loop bootstrap already wires Playwright MCP explicitly through the generated repo-local `CODEX_HOME` config in `scripts/haac_loop.py`; using it for public URL verification is not optional when available.

The repo-local Ralph loop prefers these local skills when present:

- `openspec-apply-change`
- `openspec-propose`
- `haac-loop-review`
- `haac-spec-discovery`
- `haac-sidecar-subagents`
- `caveman` when token efficiency is useful

## Security Guardrails

- Do not echo secret values into logs or summaries.
- Do not stage or publish private keys, `.env`, or derived sensitive files unless the active spec explicitly covers secret handling and the file is intended to be tracked.
- Prefer namespace-scoped secrets over cluster-wide scope unless cross-namespace use is required.
- Avoid disabling SSH host verification unless the active spec documents the reason and the recovery plan.

## Definition Of Done

A change touching the bootstrap path is only done when the active spec records:

- `doctor`
- `plan`
- `helm template`
- `kubectl kustomize`
- `task -n up`
- `task up` or wrapper equivalent when the environment is available

For `task up`, success means:

- infra created or reconciled
- K3s reachable
- ArgoCD root, platform, and workloads healthy enough for intended traffic
- Cloudflare reconciled
- a final summary of visitable URLs is printed with auth expectation and status
- those URLs are browser-checked with Playwright MCP when the loop is performing the verification round and Playwright MCP is available

## Editing Guidance

- Prefer templates over repeated literals.
- Keep generated outputs readable, but edit the source template first.
- When fixing the pipeline, preserve resumability and idempotence.
- When in doubt, improve observability before adding more automation.
- When adding loop behavior, keep the runner thin and move policy into docs, specs, and skills.
