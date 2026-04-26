# HaaC Loop Subagents

Subagents are sidecars. Main agent owns the round.

## Default

- main agent owns scope, diff, and final decision
- use 0-3 sidecars per round
- sidecars must be narrow and evidence-driven
- do not delegate the critical path if the main agent needs the result immediately

## Good Sidecar Jobs

- architecture consistency check across `tofu/`, `ansible/`, `k8s/`, and `scripts/`
- security review of secrets, auth, Cloudflare, and bootstrap trust boundaries
- OpenSpec change structure and task decomposition review
- render/validation triage for Helm, Kustomize, or Task output
- documentation drift detection

## Bad Sidecar Jobs

- full repo ownership
- broad speculative rewrites
- duplicate task implementation
- inventing backlog without evidence

## Prompt Shape

State:

- exact area
- read-only or edit allowed
- exact question
- expected output format

Example:

- `Inspect internal/cli plus Taskfile.yml. Read-only. Return top 3 reliability gaps that could break haac up on Windows or Linux.`
