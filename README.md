# HaaC (Home as Code)

This repository provisions and operates a Proxmox + K3s homelab/media stack with:

- OpenTofu for LXC infrastructure
- Ansible for host and node configuration
- ArgoCD for GitOps reconciliation
- Helm for the dynamic application stack
- Kustomize for the GitOps topology and app-of-apps layout

The stack includes the `*arr` suite, Jellyfin, qBittorrent/QUI, Authelia, Headlamp, Cloudflare Tunnel, Longhorn, monitoring, and security services.

## Repository Layout

- `tofu/`: Proxmox infrastructure, LXC modules, inventory generation
- `ansible/`: Proxmox baseline, K3s install, node runtime config, GitOps bootstrap
- `k8s/bootstrap/root/`: namespaces, ArgoCD projects, and the two root GitOps apps
- `k8s/platform/`: ArgoCD self-management, infra apps, Traefik config, NFD
- `k8s/workloads/`: workload-facing ArgoCD applications
- `k8s/charts/haac-stack/`: the dynamic workload stack rendered by Helm
- `scripts/`: cross-platform orchestration helpers used by Task and the local wrappers

## GitOps Layout

ArgoCD `Application` objects live in the `argocd` namespace because ArgoCD watches them there. That does not mean the workloads run in `argocd`.

Longhorn and `haac-stack` are a good example of this distinction:

- their ArgoCD `Application` objects live in `argocd`
- their real workloads run in destination namespaces such as `longhorn-system`, `media`, and `mgmt`
- they communicate normally over Kubernetes Service DNS, for example `service.namespace.svc.cluster.local`

- `k8s/bootstrap/root/` bootstraps namespaces, `AppProject`s, and two root apps.
- `k8s/platform/` owns cluster services such as ArgoCD, Longhorn, monitoring, Falco, Traefik config, and Node Feature Discovery.
- `k8s/workloads/` owns the application layer, currently the `haac-stack` Helm app.

This is the logical split:

- ArgoCD control plane: `argocd`
- Platform namespaces: `argocd`, `longhorn-system`, `monitoring`, `security`, `chaos`, `kube-system`, `node-feature-discovery`
- Workload namespaces: `media`, `mgmt`, `cloudflared`

Communication between apps does not depend on sharing a namespace. Kubernetes services resolve across namespaces with normal DNS and service references, and ingress/gateway routing is cluster-wide.

## Helm vs Kustomize

Kustomize is used for the GitOps structure and static platform manifests.

Helm is kept for `k8s/charts/haac-stack/` because that layer is heavily parameterized:

- shared image pins
- shared ingress generation
- env-driven secret hydration
- repeated cross-service settings
- multi-namespace rendering from one source of truth

Replacing that stack with raw YAML plus overlays would reduce readability and DRY, not improve it.

## Windows and Linux

Portable CLI tools are bootstrapped into platform-specific directories under `.tools/`:

- `.tools/windows-amd64/bin/` on Windows
- `.tools/linux-amd64/bin/` on Linux/WSL
- `.tools/darwin-arm64/bin/` or `.tools/darwin-amd64/bin/` on macOS

The portable set is:

- `tofu`
- `helm`
- `kubectl`
- `kubeseal`
- `task`

The remaining system dependencies stay OS-level on purpose:

- `python`
- `git`
- `ssh`
- `wsl` on Windows
- `ansible-playbook` on Linux or inside WSL on Windows

If you do not have a global `task`, use the repo-local wrappers:

- Windows: `.\haac.ps1 up`
- Linux/macOS: `sh ./haac.sh up`

If you do have `task` installed, `task up` still works.

## Quick Start

1. Copy `.env.example` to `.env`.
2. Fill in the required secrets and infrastructure values.
3. Run `python scripts/haac.py install-tools` or the local wrapper:
   - Windows: `.\haac.ps1 install-tools`
   - Linux/macOS: `sh ./haac.sh install-tools`
4. Run `python scripts/haac.py doctor` or:
   - Windows: `.\haac.ps1 doctor`
   - Linux/macOS: `sh ./haac.sh doctor`
5. Run the full bootstrap:
   - Windows: `.\haac.ps1 up`
   - Linux/macOS: `sh ./haac.sh up`
   - or `task up` if Task is already installed globally

On Linux, set `PYTHON_CMD=python3` in `.env` if your distro does not provide a `python` alias.

## Main Commands

- `install-tools`: bootstrap `.tools/<os>-<arch>/bin` and, on Windows, the WSL control-node packages plus the Linux portable toolchain used from WSL
- `doctor`: verify local prerequisites
- `up`: full provisioning and GitOps bootstrap
- `plan`: OpenTofu plan only
- `configure-os`: Ansible only
- `deploy-local`: local Helm deploy for the workload stack
- `verify-all`: cluster and endpoint checks
- `down`: graceful shutdown and destroy

## Storage / Samba

The cluster does not mount Samba directly from inside pods.

The current storage path is:

1. Proxmox mounts the SMB/CIFS share with Ansible.
2. That host path is bind-mounted into the LXC nodes.
3. K3s workloads consume the mounted path from the nodes.

So yes, the cluster can use the NAS, but today it does so through the Proxmox host mount and LXC bind mounts, not through a CSI SMB driver inside Kubernetes.

## Notes

- `.env` is the source of truth for GitOps repo settings, local tool pins, LXC flags, workstation settings, and all Terraform inputs. `Taskfile.yml` no longer defines `TF_VAR_*`; that mapping is generated centrally by `scripts/haac.py`.
- `HAAC_KUBECTL_VERSION` controls the local workstation binary. `HAAC_CLUSTER_KUBECTL_IMAGE_TAG` controls the in-cluster helper image. They can differ because image publishing cadence does not always match the official client release cadence.
- LXC should remain `unprivileged` by default; K3s, GPU, TUN, and eBPF exceptions are centrally gated with env flags.
- `task up` includes automatic Cloudflare tunnel/DNS reconciliation through the Cloudflare API.
- GPU workload scheduling uses standard Kubernetes GPU resources; Node Feature Discovery is used for infrastructure-side GPU discovery.
- `task -n up` is a Task dry-run flag. It is not implemented in `scripts/haac.py`; it comes from Task itself and shows what would run without executing it.

See `ARCHITECTURE.md` for the full architecture and `HOMELAB_SERVICES.md` for the service inventory.
