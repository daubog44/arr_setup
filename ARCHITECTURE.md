# HaaC Architecture

## Overview

HaaC is a Proxmox + K3s homelab managed as code.

The system is split into four layers:

1. OpenTofu provisions the LXC nodes on Proxmox.
2. Ansible configures Proxmox, installs K3s, mounts NAS storage, and applies host-level compatibility settings.
3. A repo-local bootstrap step installs ArgoCD from the vendored install overlay, then ArgoCD reconciles the cluster from Git.
4. Helm renders the dynamic workload stack, while Kustomize organizes the GitOps control plane.

## Node Model

The cluster is built on LXC containers and is intended to stay unprivileged by default.

Why:

- better isolation than privileged containers
- smaller blast radius on the Proxmox host
- no need to grant full container privileges just to satisfy K3s or GPU support

Compatibility exceptions are centrally controlled from `.env`:

- `LXC_K3S_COMPAT_MODE`
- `LXC_ENABLE_GPU_PASSTHROUGH`
- `LXC_ENABLE_TUN`
- `LXC_ENABLE_EBPF_MOUNTS`

This keeps the security model explicit and auditable instead of hiding it in ad-hoc playbook edits.

## GitOps Topology

The repository now uses a layered GitOps layout:

- `k8s/bootstrap/root/`
  - namespaces
  - ArgoCD `AppProject`s
  - root applications: `haac-platform` and `haac-workloads`
- `k8s/platform/`
  - ArgoCD self-management
  - Longhorn
  - monitoring and security apps
  - Traefik config
  - Node Feature Discovery
- `k8s/workloads/`
  - workload applications such as `haac-stack`
- `k8s/charts/haac-stack/`
  - the dynamic multi-service workload chart

Important distinction:

- ArgoCD `Application` CRs live in namespace `argocd`
- the workloads they manage run in their own destination namespaces

So Longhorn and `haac-stack` can both be "in ArgoCD" from a control-plane perspective while still being fully separated operationally:

- the `Application` objects live in `argocd`
- the Longhorn pods run in `longhorn-system`
- the `haac-stack` pods run in namespaces such as `media` and `mgmt`
- cross-namespace communication works through normal Kubernetes Service DNS such as `service.namespace.svc.cluster.local`

## Namespaces

The namespace split is logical rather than purely technical:

- `argocd`: GitOps control plane
- `media`: media and downloader workloads
- `mgmt`: management apps and automation
- `cloudflared`: tunnel deployment
- `longhorn-system`: distributed storage
- `monitoring`: metrics and dashboards
- `security`: runtime and security tooling
- `chaos`: resilience testing
- `kube-system`: K3s system components
- `node-feature-discovery`: hardware discovery

Cross-namespace communication is normal Kubernetes behavior. Services communicate through cluster DNS and service routing, not by sharing a namespace.

## Storage Flow

NAS access is currently host-mediated.

Flow:

1. Ansible installs `cifs-utils` on Proxmox.
2. Proxmox mounts the SMB share to `HOST_NAS_PATH`.
3. The host path is bind-mounted into the LXC nodes.
4. Pods consume the mounted storage from the node filesystem.

This means the cluster can use the NAS, but it is not using an in-cluster SMB CSI driver.

Longhorn backups also target that mounted NAS path.

## GPU Flow

GPU support is split into two concerns:

1. Host/runtime enablement
   - Proxmox and LXC passthrough
   - K3s runtime configuration
2. Kubernetes scheduling
   - Node Feature Discovery discovers hardware
   - device plugins are placed using NFD-derived labels
   - actual GPU workloads request `nvidia.com/gpu`

This is more standard than relying on custom labels applied by Ansible for scheduling decisions.

## Why Helm Still Exists

Helm remains the right tool for `haac-stack` because that layer is highly parameterized and multi-tenant across namespaces.

The chart centralizes:

- images and versions
- ingress generation
- reusable service settings
- secrets generated from `.env`
- repeated patterns across media and management services

Kustomize is used where structure and composition help most. Helm is used where templating and DRY help most.

## Local Orchestration

The portable control plane for the workstation is staged: `task up` remains the product surface, wrapper entrypoints can route through the repo-local Go/Cobra CLI while preserving raw Task argument semantics, and Python remains the compatibility bridge for commands that have not been ported yet. The supported wrapper surface remains the public Task contract, not `internal:*` helper tasks.

High-risk reusable helper surfaces are now split out under `scripts/haaclib/` for:

- secret redaction
- SSH trust defaults
- Authelia password/hash derivation
- GitOps rendering
- public endpoint probing

It is responsible for:

- bootstrap of `.tools/<os>-<arch>/bin`
- Windows/WSL coordination
- kubeconfig handling and SSH tunnels
- secret generation
- ArgoCD bootstrap
- Cloudflare tunnel and DNS reconciliation
- local fallback deploy and verification

## Bootstrap Contract

The one-command bootstrap contract is stage-based and shared by `task up`, `.\haac.ps1 up`, and `sh ./haac.sh up`.

The required order is:

1. preflight: validate `.env` and workstation tooling
2. infra provisioning: OpenTofu
3. node configuration: Ansible plus K3s service, flannel, and cluster node-readiness gating before GitOps bootstrap
4. secret and GitOps publication
5. staged ArgoCD readiness gates
6. Cloudflare publication
7. cluster verification
8. public URL verification and summary

`.env` is the input source of truth for both bootstrap prerequisites and public routing. The final public URL report is derived from the Helm ingress definitions in `k8s/charts/haac-stack/config-templates/values.yaml.template` and the generated `values.yaml`, not from a duplicated hardcoded list.

That ingress catalog is now also the Homepage source of truth. Homepage links, public endpoint verification, `HTTPRoute` generation, and Cloudflare publication are all derived from the same declared route set. Each published route must explicitly declare one auth strategy: `public`, `edge_forward_auth`, `native_oidc`, or `app_native`. Template rendering and endpoint verification both fail closed if the strategy is missing or invalid. Unsupported hosts are not published through the Cloudflare tunnel and are not part of the supported public surface.

`.env` is also the source of truth for the operator identity defaults. `HAAC_MAIN_USERNAME`, `HAAC_MAIN_PASSWORD`, `HAAC_MAIN_EMAIL`, and `HAAC_MAIN_NAME` seed the control-plane human login defaults when a service-specific override is absent. That default layer covers Authelia, ArgoCD local auth, Grafana local admin, Semaphore admin, and Litmus admin. The downloader local auth stays separate by default through `QBITTORRENT_USERNAME` and `QUI_PASSWORD`; if the operator intentionally wants one main username/password across those lower-trust apps too, `HAAC_ENABLE_SHARED_DOWNLOADER_CREDENTIALS=true` makes that inheritance explicit instead of leaving it as an undocumented fallback. `AUTHELIA_ADMIN_PASSWORD_HASH` remains a derived compatibility value: if the effective Authelia admin password is present and the stored hash does not match, hydration regenerates the hash before sealing the Authelia config.

That identity layer applies only to human login defaults. OIDC client secrets, cookie/encryption secrets, and database passwords remain separate opaque inputs in `.env` and are not derived from the main operator password. Control-plane services must not fall back to downloader passwords.

For Proxmox connectivity, `.env` separates node identity from workstation access: `MASTER_TARGET_NODE` is the Proxmox node name used by resources and generated inventory, while `PROXMOX_ACCESS_HOST` is the API/SSH host used by preflight, OpenTofu provider access, and tunnel setup. If the node name already resolves from the operator workstation, the access host falls back to `MASTER_TARGET_NODE`.

`.env` is also the single source of truth for Terraform inputs. The wrapper translates env values into `TF_VAR_*` centrally before calling OpenTofu, instead of duplicating that mapping in `Taskfile.yml`.

Publication scope is now explicit too: the supported Task pipeline publishes only generated GitOps artifacts.

Git merge policy is separate from the main bootstrap path. `task sync` owns checkpoint plus safe fast-forward merge policy and fails closed on divergence; `task up` only publishes GitOps outputs, unwinds its own publication race if the remote branch moves during push, and points the operator back to `task sync` when merge policy is required.

## Recurring Work Boundaries

Recurring work is split by execution plane, not by naming convention.

- Kubernetes CronJobs are used when the work is cluster-local and should execute inside the cluster:
  - `descheduler`
  - `recyclarr`
  - `k3s-sqlite-backup`
- Semaphore schedules are used when the work needs Ansible inventory, jump-host access, maintenance credentials, serialized rollout, or reboot-aware host maintenance:
  - rolling K3s node updates
  - rolling Proxmox host updates
  - K3s database restore as an on-demand operator template

This avoids forcing infra maintenance into Kubernetes jobs that would need the same external trust and inventory boundary anyway.

## Falco On Unprivileged LXC

Falco runtime is supported in this repo through a dedicated host-side sensor on the Proxmox node. The previous in-cluster sensor model for unprivileged LXC workers was rejected by live evidence: even after the kernel metadata mounts were fixed, `modern_ebpf` still failed inside the guest on BPF ring-buffer setup.

The supported path is:

- the platform layer deploys the upstream `falcosidekick` chart in-cluster
- the cluster exposes a stable internal ingest `NodePort` plus the protected Falcosidekick UI
- the Proxmox host installs the official Falco package and runs the `modern_ebpf` engine directly on the host
- the host Falco service forwards events into the cluster through `http_output`

This keeps runtime coverage working in the current environment without pretending the unprivileged LXC guests can host the syscall sensor reliably.

If global Task is missing, use:

- Windows: `.\haac.ps1 up`
- Linux/macOS: `sh ./haac.sh up`

These wrappers bootstrap the local Task binary and invoke the same `Taskfile.yml`.
