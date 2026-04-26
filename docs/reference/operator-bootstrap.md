# Operator Bootstrap Reference

This guide explains the repo-managed operator path behind `haac up`.

## What `haac up` Owns

The supported entrypoints are:

- direct CLI from an initialized workspace: `haac up`
- optional Task alias: `task up`

The direct `haac` command owns the bootstrap pipeline. Taskfiles remain optional aliases around public `haac` commands; shell and PowerShell wrappers are intentionally absent.

## Phase Model

`haac up` is expected to be convergent. A partial failure should normally be recoverable by rerunning the same command unless the output explicitly says manual intervention is required first.

The phase order is:

1. preflight
   - `check-env`
   - `doctor`
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
- `internal/cli/`: the Go/Cobra operator backend, including phase engine, generated artifact wiring, GitOps publication, API bootstraps, verification flows, and recovery commands
- `scripts/`: loop helpers and legacy maintenance utilities that are not part of the supported product backend

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

- `haac up`: full convergent reconciliation
- `haac reconcile-media-stack`: rerun only the supported media bootstrap and API wiring
- `haac wait-for-stack`: staged GitOps readiness only
- `haac verify-cluster` plus `haac verify-web`: cluster + public surface verification
- `haac diagnose-edge`: classify Cloudflare-fronted `403` failures across Cloudflare token scope, tunnel/origin evidence, and CrowdSec decisions
- `haac clear-crowdsec-operator-ban`: remove temporary CrowdSec decisions for the current operator public IP
- `haac verify-arr-flow`: media request-to-playback acceptance path
- `haac down`: graceful shutdown plus destroy

The Git boundary is also explicit:

- `haac sync-repo` owns the fetch/merge policy before bootstrap when the local branch must be realigned explicitly
- `haac up` and `haac push-changes` are publish-only
- if the branch is behind or diverged, the operator must resolve that explicitly through the supported sync path

## Generated Artifact Rules

Keep these invariants intact:

- do not edit generated secrets as primary sources
- do not copy `.env` values into code except in intended generated outputs
- keep temporary operator artifacts under `.tmp/`
- prefer changing templates or the supported `haac` implementation over hand-editing rendered YAML

## Legacy Surfaces

The supported operator CLI is the Cobra-owned `haac` surface. The public `haac` command tree no longer exposes Python-backed maintenance subcommands, and `haac up` does not execute the historical Python bootstrap backend.

The remaining Python files are loop helpers, tests, or historical maintenance artifacts. They are not part of the supported operator path.

Operators should treat those files as implementation details for development workflows, not as supported direct CLI entrypoints. The standalone distribution path is `haac init` -> fill `.env` -> `haac install-tools` -> `haac up`.

## Cloudflare Edge Diagnostics

`haac sync-cloudflare` owns tunnel ingress and DNS, but Cloudflare security policy APIs require broader token scope than DNS/tunnel reconciliation. For full edge remediation automation the token must be able to read zone settings, read WAF/rulesets, and read/edit IP access rules. If those scopes are absent, `haac diagnose-edge` reports the exact missing API surface and the manual dashboard path instead of retrying blindly.

Optional `.env` input:

- `CLOUDFLARE_VERIFICATION_ALLOWLIST_IPS`: comma-separated operator IPs to allow when running `haac diagnose-edge --apply-operator-allowlist`; if unset, the CLI uses the currently detected public IP.

## Cold-Cycle Acceptance

The destructive acceptance surface is:

1. `haac down`
2. `haac up`
3. `haac wait-for-stack`
4. `haac verify-cluster` and `haac verify-web`
5. `haac verify-arr-flow`

That sequence is the strongest proof that the stack is both bootstrap-capable and rerunnable from a cold start.
