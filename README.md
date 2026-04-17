# HaaC (Home as Code)

This repository provisions and operates a Proxmox + K3s homelab/media stack with:

- OpenTofu for LXC infrastructure
- Ansible for host and node configuration
- ArgoCD for GitOps reconciliation
- Helm for the dynamic application stack
- Kustomize for the GitOps topology and app-of-apps layout

The stack includes the `*arr` suite, Jellyfin, qBittorrent/QUI, Authelia, Headlamp, Cloudflare Tunnel, Longhorn, monitoring, and security services.

`task up` uses a state-safe OpenTofu apply path for existing LXC nodes because the current `bpg/proxmox` provider cannot round-trip HAAC-managed raw LXC config such as `idmap`. Keep `task plan` as the diagnostic path when you want a full provider-refresh view of unsupported drift.

Bootstrap-critical `mgmt` stateful workloads default to `local-path` in this repo. The current Proxmox LXC + ZFS substrate does not provide a reliable Longhorn replica backend for those services, so `task up` keeps the control plane and management layer on node-local storage while Longhorn remains available as a platform component.

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
4. Run `python scripts/haac.py check-env` or:
   - Windows: `.\haac.ps1 check-env`
   - Linux/macOS: `sh ./haac.sh check-env`
5. Run `python scripts/haac.py doctor` or:
   - Windows: `.\haac.ps1 doctor`
   - Linux/macOS: `sh ./haac.sh doctor`
6. Run the full bootstrap:
   - Windows: `.\haac.ps1 up`
   - Linux/macOS: `sh ./haac.sh up`
   - or `task up` if Task is already installed globally

On Linux, set `PYTHON_CMD=python3` in `.env` if your distro does not provide a `python` alias.

## Main Commands

- `install-tools`: bootstrap `.tools/<os>-<arch>/bin` and, on Windows, the WSL control-node packages plus the Linux portable toolchain used from WSL
- `check-env`: verify required `.env` inputs plus workstation-to-Proxmox API and SSH reachability before bootstrap
- `doctor`: verify local prerequisites
- `up`: full provisioning and GitOps bootstrap
- `plan`: OpenTofu plan only
- `configure-os`: Ansible only
- `deploy-local`: local Helm deploy for the workload stack
- `verify-all`: cluster and endpoint checks
- `down`: graceful shutdown and destroy

## Task Up Contract

`task up`, `.\haac.ps1 up`, and `sh ./haac.sh up` all invoke the same Task pipeline. The shell wrappers now prefer the repo-local Go/Cobra entrypoint when `go` is available, pass raw Task arguments through unchanged, and fall back to the Python bridge if the staged Go path is unavailable or fails.

That bootstrap path is also the supported rerun path. A partial or previously successful run should be recoverable by rerunning the same command unless the failure output explicitly says manual intervention is required.

The logical phase order is:

1. preflight: `check-env`, `doctor`
2. infra provisioning: OpenTofu init and apply through the explicit `provision-infra` phase
3. node configuration: Ansible plus K3s service, flannel, and node-readiness gating before GitOps bootstrap
4. secret and GitOps publication: regenerate rendered artifacts, push the GitOps source of truth, bootstrap ArgoCD
5. staged ArgoCD readiness: platform root, ArgoCD self-management, workloads root, `haac-stack`
6. Cloudflare publication: tunnel ingress plus DNS reconciliation
7. cluster verification
8. public URL verification and final summary

The minimum `.env` inputs for `task up` are grouped into three surfaces:

- infra and storage: `LXC_PASSWORD`, `LXC_MASTER_HOSTNAME`, `NAS_ADDRESS`, `HOST_NAS_PATH`, `NAS_PATH`, `NAS_SHARE_NAME`, `SMB_USER`, `SMB_PASSWORD`, `STORAGE_UID`, `STORAGE_GID`
- GitOps publication: `GITOPS_REPO_URL`, `GITOPS_REPO_REVISION`
- public routing: `DOMAIN_NAME`, `CLOUDFLARE_API_TOKEN`, `CLOUDFLARE_ACCOUNT_ID`, `CLOUDFLARE_ZONE_ID`, `CLOUDFLARE_TUNNEL_TOKEN`
- operator identity defaults: `HAAC_MAIN_USERNAME`, `HAAC_MAIN_PASSWORD`, `HAAC_MAIN_EMAIL`, `HAAC_MAIN_NAME`
- optional downloader credential sharing: `HAAC_ENABLE_SHARED_DOWNLOADER_CREDENTIALS`
- downloader local auth: `QBITTORRENT_USERNAME`, `QUI_PASSWORD`
- Litmus MongoDB backend: `LITMUS_MONGODB_ROOT_PASSWORD`, `LITMUS_MONGODB_REPLICA_SET_KEY`

The main operator identity is the default login layer for local Authelia auth, ArgoCD local auth, Grafana local admin, Semaphore admin, and Litmus admin. The downloader local auth stays explicit by default. If you want one main username/password across qBittorrent and QUI too, set `HAAC_ENABLE_SHARED_DOWNLOADER_CREDENTIALS=true` and leave the dedicated downloader vars unset, or override them explicitly if you need separate values.

Opaque machine secrets stay separate. OIDC client secrets, cookie keys, encryption keys, DB passwords, and similar bootstrap internals do not derive from `HAAC_MAIN_PASSWORD`. Grafana no longer falls back to downloader credentials either; it uses the effective admin identity layer only.

The supported login model is:

- `HAAC_MAIN_*`: default human operator identity for Authelia, ArgoCD, Grafana, Semaphore, and Litmus
- `HAAC_ENABLE_SHARED_DOWNLOADER_CREDENTIALS=true`: optional opt-in to let qBittorrent and QUI inherit `HAAC_MAIN_*`
- `QBITTORRENT_USERNAME` and `QUI_PASSWORD`: dedicated downloader auth when you want a lower-trust boundary
- `LITMUS_MONGODB_ROOT_PASSWORD` and `LITMUS_MONGODB_REPLICA_SET_KEY`: stable technical secrets for the Litmus MongoDB subchart; pin them so Argo/Helm do not rotate the replica-set secret on every render
- `*_OIDC_SECRET`, `*_COOKIE_*`, DB passwords, encryption keys: opaque bootstrap secrets that must stay separate from the human login defaults

`LXC_PASSWORD` remains the documented password source of truth. Supporting `scripts/haac.py` bootstrap commands reuse it as the default Proxmox host password unless a caller explicitly overrides `PROXMOX_HOST_PASSWORD`.

`task up` is now publish-only on the Git boundary. It stages only generated GitOps artifacts and refuses to merge remote state when the branch is behind or diverged.

Git merge policy is explicit. `task sync` owns the local checkpoint plus safe fast-forward merge path, fails closed on divergence, and leaves manual conflict resolution explicit. Broad repo publication is no longer part of the supported Task operator surface.

`MASTER_TARGET_NODE` remains the Proxmox node name used inside OpenTofu and generated inventory. `PROXMOX_ACCESS_HOST` is the workstation-reachable IP or hostname used for the Proxmox API, SSH, and tunnel operations. If the node name itself already resolves locally, `PROXMOX_ACCESS_HOST` may be left unset and the bootstrap falls back to `MASTER_TARGET_NODE`.

SSH trust is no longer forced off by default. The operator path now uses a repo-local `known_hosts` file together with `StrictHostKeyChecking=accept-new`, so the first bootstrap stays practical without silently bypassing host verification on later runs.

ArgoCD bootstrap ownership is now local to the repo: Ansible prepares the cluster prerequisites, while `scripts/haac.py deploy-argocd` installs ArgoCD from `k8s/platform/argocd/install-overlay` and only then applies the app-of-apps root.

Cloudflare Tunnel autoupdate is configurable again through `.env` via `HAAC_ENABLE_CLOUDFLARED_AUTOUPDATE`. Trivy remains intentionally bounded to avoid control-plane churn on the single-master SQLite/Kine topology.

Preflight now includes local env completeness, workstation tooling, writable GitOps sync, and validation of the effective Proxmox API/SSH access host before provisioning starts. OpenTofu, Ansible, ArgoCD degradation, and Cloudflare API failures stop the run immediately. `configure-os` also stops before GitOps bootstrap if K3s service recovery does not yield local flannel subnet state or a fully `Ready` node set. Readiness and endpoint checks retry until timeout. When a phase still fails, the operator output now reports the failing phase, the last verified phase, and whether rerunning `task up` is the normal recovery path. The detailed operator contract lives in `docs/runbooks/task-up.md`.

The official public URL surface is only the ingress catalog declared in `k8s/charts/haac-stack/config-templates/values.yaml.template` and rendered into `k8s/charts/haac-stack/values.yaml`. `verify-web`, Homepage, the generated `HTTPRoute` set, and Cloudflare publication all derive from that same source of truth. Every published route must declare an explicit `auth_strategy` (`public`, `edge_forward_auth`, `native_oidc`, or `app_native`), and rendering fails closed if a route omits that field. Hosts outside the official catalog are unsupported and are not published through the Cloudflare tunnel.

## Ralph Loop

This repo includes a CodexPotter-backed Ralph loop that works on top of the official OpenSpec CLI.

Loop goals:

- apply the current active OpenSpec change
- keep validation, code review, and security review in the loop
- self-improve by opening a new OpenSpec change if the loop detects a real missing capability in its own bootstrap, review gates, or discovery process

Main loop entrypoints:

- `task loop:check`
- `task loop:yolo SLUG=task-up ROUNDS=10`
- `task loop:yolo:checked SLUG=task-up ROUNDS=10`
- `task loop:discover SLUG=bootstrap-gap ROUNDS=3`

Loop transcript verbosity is controlled by `HAAC_POTTER_VERBOSITY`:

- `minimal`: compact terminal output
- `simple`: more explicit tool/edit transcript output

`task loop:yolo` is apply-first, not apply-only. During the same run it may:

- continue the first active OpenSpec change
- switch to narrow discovery if no active change remains
- open one new evidence-backed OpenSpec change if the loop detects a missing capability in bootstrap, review, validation, or its own runner

That discovery scope is broader than the loop itself. It can target real HaaC gaps in:

- OpenTofu, Ansible, K3s, ArgoCD, Helm, Kustomize, and Cloudflare flow
- DRY and centralization regressions
- security and trust-boundary issues
- cross-platform Windows/Linux operator behavior
- storage, GPU, networking, and post-setup automation mismatches

Each discovered gap should become an OpenSpec change with a concrete proposed solution, not just a note.

This includes loop-internal capability gaps too. If the model is missing the right repo-specific behavior, the loop may create or refine:

- `scripts/haac_loop.py`
- `docs/haac-loop-prompt.md`
- `docs/loop-*.md`
- repo-local skills under `.codex/skills/`
- role prompts under `openspec/agents/`
- `.codex/hooks.json` and related bootstrap glue

When a round reaches public endpoint verification, the loop is expected to use Playwright MCP for browser-level navigation of the emitted URLs, not only the HTTP-level checks from `verify-web`.

Supporting files:

- `docs/haac-loop-prompt.md`
- `docs/loop-review.md`
- `docs/loop-discovery.md`
- `docs/loop-subagents.md`
- `docs/loop-worklog.md`
- `openspec/agents/`
- `.codex/skills/haac-*`

The loop uses the same source of truth as the operator workflow: `.env`, `Taskfile.yml`, `scripts/haac.py`, and the active OpenSpec changes.

## Spec-Driven Workflow

The repo now uses a spec-driven workflow documented in `AGENTS.md` and `openspec/`.

- `AGENTS.md` is the operator contract for the repository.
- `openspec list --json` is the source of truth for which changes are currently active.
- `openspec/specs/` contains the stable capability contracts that survive after archive.
- `openspec/changes/` contains active change proposals and task work.
- `openspec/changes/archive/` preserves the history of completed changes after their stable specs are synced.
- `docs/runbooks/task-up.md` is the operator runbook for the main bootstrap path.

For Codex users, the repo also includes a project-local SessionStart hook scaffold in `.codex/hooks.json` that can be used to enable a terse "caveman" session banner.

## Storage / Samba

The cluster does not mount Samba directly from inside pods.

The current storage path is:

1. Proxmox mounts the SMB/CIFS share with Ansible.
2. That host path is bind-mounted into the LXC nodes.
3. K3s workloads consume the mounted path from the nodes.

So yes, the cluster can use the NAS, but today it does so through the Proxmox host mount and LXC bind mounts, not through a CSI SMB driver inside Kubernetes.

## Recurring Jobs

Recurring work is intentionally split across two execution planes.

- Kubernetes CronJobs own in-cluster recurring work:
  - `kube-system/descheduler`
  - `media/recyclarr`
  - `mgmt/k3s-sqlite-backup`
- Semaphore schedules own infra maintenance that needs Ansible inventory, jump-host access, maintenance SSH credentials, serialized rollout, or host reboot semantics:
  - `Rolling OS Update - K3s Nodes`
  - `Rolling OS Update - Proxmox Hosts`
  - `Restore K3s Database (from NAS)` as an on-demand template

That split is deliberate. Cluster-local jobs stay in Kubernetes; infra maintenance stays in Semaphore.

## Notes

- `.env` is the source of truth for GitOps repo settings, local tool pins, LXC flags, workstation settings, and all Terraform inputs. `Taskfile.yml` no longer defines `TF_VAR_*`; that mapping is generated centrally by `scripts/haac.py`, while internal bootstrap subtasks now live under `Taskfile.internal.yml` and the staged Cobra bridge can pass the same Task arguments through unchanged without exposing `internal:*` tasks as part of the supported wrapper surface.
- `HAAC_KUBECTL_VERSION` controls the local workstation binary. `HAAC_CLUSTER_KUBECTL_IMAGE_TAG` controls the in-cluster helper image. They can differ because image publishing cadence does not always match the official client release cadence.
- LXC should remain `unprivileged` by default; K3s, GPU, TUN, and eBPF exceptions are centrally gated with env flags.
- `task up` includes automatic Cloudflare tunnel/DNS reconciliation through the Cloudflare API.
- GPU workload scheduling uses standard Kubernetes GPU resources; Node Feature Discovery is used for infrastructure-side GPU discovery.
- Falco runtime is supported through a dedicated host-side sensor on the Proxmox node, not through an in-cluster DaemonSet on unprivileged LXC workers.
- When `HAAC_ENABLE_FALCO=true`, the platform layer deploys `falcosidekick` in-cluster for alert ingest plus the protected UI, and the Proxmox host installs the Falco package with the `modern_ebpf` engine and forwards events to the cluster-side ingest service on the declared K3s master IP.
- Falco no longer depends on `haac.io/falco-runtime` worker labels to become healthy. Those labels can remain for future experiments, but they are not part of the supported runtime path anymore.
- `task -n up` is a Task dry-run flag. It is not implemented in `scripts/haac.py`; it comes from Task itself and shows what would run without executing it.

See `ARCHITECTURE.md` for the full architecture and `HOMELAB_SERVICES.md` for the service inventory.
