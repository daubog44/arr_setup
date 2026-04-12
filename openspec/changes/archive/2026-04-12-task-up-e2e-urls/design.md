## Context

The repo already follows the correct macro-flow for the target system:

- OpenTofu creates Proxmox LXC infrastructure
- Ansible configures Proxmox and K3s nodes
- ArgoCD bootstraps and reconciles platform plus workloads
- Cloudflare Tunnel and DNS publish ingress externally

The main gap is not architecture selection; it is the operational contract of the bootstrap path. `task up` needs stronger preflight checks, clearer phase boundaries, and a deterministic final report of public URLs.

## Goals / Non-Goals

**Goals:**
- Define `task up` as the single supported bootstrap command.
- Make the pipeline phases explicit and observable.
- Require a final service URL report derived from one source of truth.
- Improve failure reporting so users know which phase failed and what to inspect next.
- Keep the workflow cross-platform across Windows and Linux.

**Non-Goals:**
- Replace Helm, Kustomize, OpenTofu, or Ansible.
- Redesign secrets management in this change.
- Rework the privilege model of the LXC nodes.
- Solve every cluster-runtime issue within the spec itself.

## Decisions

- Treat `.env` as the canonical input surface for bootstrap configuration and public domain generation.
- Use `Taskfile.yml` plus wrappers (`haac.ps1`, `haac.sh`) as the user-facing orchestration contract.
- Model `task up` as staged phases:
  1. local preflight
  2. infra provisioning
  3. node configuration
  4. secret and GitOps publication
  5. ArgoCD and workload readiness
  6. Cloudflare publication
  7. cluster verification
  8. public URL summary
- Derive the public URL list from configured ingress data rather than a duplicated hardcoded list when possible.
- Treat final public URL output as part of success, not as optional logging.

## Risks / Trade-offs

- Making the contract stricter may surface failures earlier that previously stayed hidden.
- Some failures will still reflect live cluster state, not wrapper logic; the benefit is better diagnosis, not guaranteed runtime success.
- Cloudflare publication ordering may need a second pass if platform readiness remains too coarse.
