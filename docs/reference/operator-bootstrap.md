# Operator Bootstrap Reference

This guide explains the repo-managed operator path behind `task up`.

## What `task up` Owns

The supported entrypoints are:

- Windows: `.\haac.ps1 up`
- Linux/macOS: `sh ./haac.sh up`
- Global Task: `task up`

All three entrypoints drive the same bootstrap pipeline through `Taskfile.yml`, `Taskfile.internal.yml`, and the supported `haac` Cobra surface.

## Phase Model

`task up` is expected to be convergent. A partial failure should normally be recoverable by rerunning the same command unless the output explicitly says manual intervention is required first.

The phase order is:

1. preflight
   - `check-env`
   - `doctor`
   - `sync`
2. infrastructure provisioning
   - OpenTofu init/apply in `tofu/`
3. node configuration
   - Ansible in `ansible/`
   - K3s readiness and flannel/node gates
4. secret and GitOps publication
   - generate sealed secrets from `.env`
   - push only the repo-managed GitOps outputs
   - bootstrap ArgoCD
5. staged platform readiness
   - root apps
   - ArgoCD self-management
   - workloads
   - critical downloader and secret gates
6. post-install reconciles
   - security post-install
   - chaos post-install
   - media post-install
   - Cloudflare edge reconciliation
7. verification
   - cluster verification
   - public HTTP verification
   - browser-level auth and UI verification

## Codebase Boundaries

The repository is intentionally split by responsibility:

- `tofu/`: Proxmox infrastructure, LXC topology, and generated inventory inputs
- `ansible/`: Proxmox preparation, storage mounts, K3s installation, and host-side configuration
- `k8s/bootstrap/root/`: namespaces, AppProjects, and the two root GitOps applications
- `k8s/platform/`: platform apps and cluster services such as ArgoCD, monitoring, security, storage, and ingress
- `k8s/workloads/`: workload-facing ArgoCD applications
- `k8s/charts/haac-stack/`: the Helm-rendered dynamic workload layer
- `scripts/`: bootstrap helpers, generated artifact wiring, API bootstraps, verification flows, and recovery commands

## `.env` To Generated Output Mapping

`.env` is the only supported operator input surface. The generated artifacts under `k8s/` are derived from templates and `.env`; they are not primary sources.

The main input surfaces are:

- infra and storage
  - Proxmox/LXC values
  - NAS mount settings
- GitOps publication
  - repo URL and branch
- public routing
  - domain, Cloudflare account, zone, tunnel
- operator identity
  - `HAAC_MAIN_*`
- optional media/security overrides
  - downloader, Jellyfin, Bazarr, CrowdSec, Litmus, and similar feature flags/secrets

The generation flow is centered in the supported `haac` operator surface:

- render non-secret templates
- fetch the Sealed Secrets cert when needed
- seal secrets from `.env`
- stage only the supported GitOps outputs
- refuse unsupported merge/publication behavior

## Supported Rerun Paths

The normal recovery surface is intentionally narrow:

- `task up`: full convergent reconciliation
- `task media:post-install`: rerun only the supported media bootstrap and API wiring
- `task wait-for-argocd-sync`: staged GitOps readiness only
- `task verify-all`: cluster + public surface verification
- `task verify:arr-flow`: media request-to-playback acceptance path
- `task down`: graceful shutdown plus destroy

The Git boundary is also explicit:

- `task sync` owns the fetch/merge policy before bootstrap
- `task up` and `task push-changes` are publish-only
- if the branch is behind or diverged, the operator must resolve that explicitly through the supported sync path

## Generated Artifact Rules

Keep these invariants intact:

- do not edit generated secrets as primary sources
- do not copy `.env` values into code except in intended generated outputs
- keep temporary operator artifacts under `.tmp/`
- prefer changing templates or the supported `haac` implementation over hand-editing rendered YAML

## Remaining Python Surfaces

The supported operator CLI is now the Cobra-owned `haac` surface reached through `.\haac.ps1`, `sh ./haac.sh`, or `task`.

The remaining Python scripts are not supported end-user entrypoints:

- `scripts/haac_loop.py`: Ralph loop automation and worklog/bootstrap glue
- `scripts/hydrate-authelia.py`: focused template/helper maintenance script
- `scripts/haac.py`: internal implementation module still reused by some Cobra subcommands while the larger runtime migration continues

Operators should treat those scripts as implementation details or loop/maintenance surfaces, not as the primary bootstrap contract.

## Cold-Cycle Acceptance

The destructive acceptance surface is:

1. `task down`
2. `task up`
3. `task wait-for-argocd-sync`
4. `task verify-all`
5. `task verify:arr-flow`

That sequence is the strongest proof that the stack is both bootstrap-capable and rerunnable from a cold start.
