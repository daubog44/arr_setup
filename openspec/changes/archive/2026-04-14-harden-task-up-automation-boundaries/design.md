# Design

## 1. Publication Boundaries

`PUSH_ALL` stays available as an escape hatch, but the default path becomes generated-artifacts-only:

- `sync-repo` stops auto-checkpointing unrelated work when `PUSH_ALL=false`
- `push-changes` stops auto-checkpointing unrelated work when `PUSH_ALL=false`
- the default `task up` path will fail early on dirty non-GitOps work instead of publishing it

This preserves automation while shrinking the blast radius.

## 2. Secrets and SSH Trust

Two changes are required:

- all command-failure surfaces redact known secret values before they are raised
- SSH moves from `StrictHostKeyChecking=no` to a repo-managed `accept-new` plus `known_hosts` file

`accept-new` keeps the first bootstrap practical while preventing silent trust bypass on later runs.

## 3. ArgoCD Bootstrap Ownership

Ansible should not install ArgoCD from a remote URL and then hand it off to GitOps.

Instead:

- Ansible stops after sealed-secrets and core cluster readiness
- `scripts/haac.py deploy-argocd` bootstraps ArgoCD from the vendored local repo manifests over the cluster tunnel
- the root app and self-management app then take over

This makes the repo, not a remote manifest URL, the authoritative bootstrap source.

## 4. Platform Convergence

- `node-problem-detector` currently duplicates `NODE_NAME`; remove the override and let the chart own it
- `litmus` currently deploys a replicated MongoDB topology that is unnecessary for this homelab and is the only remaining drift source; move it to a single-node topology

## 5. Explicit Authelia Password

Add `AUTHELIA_ADMIN_PASSWORD` to `.env` and `.env.example`.

Hash generation rules:

- if `AUTHELIA_ADMIN_PASSWORD` is present, it becomes the source of truth and its hash is derived automatically during hydration
- `AUTHELIA_ADMIN_PASSWORD_HASH` remains as backward-compatible fallback only

## 6. Modularization

This change does not rewrite the whole orchestrator. It extracts the high-risk reusable surfaces first:

- command redaction helpers
- Authelia password/hash hydration helpers
- SSH known-host handling helpers

That gives immediate safety wins without destabilizing the bootstrap path.
