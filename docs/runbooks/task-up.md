# Task Up Runbook

## Goal

Run one command that provisions, configures, deploys, and verifies the homelab.

That same command is also the normal recovery path after a partial or converged run. Operators should rerun `task up` unless the failure output explicitly says a manual fix is required first.

## Related References

Use these alongside this runbook when you need the full repo contract:

- `docs/reference/operator-bootstrap.md`
- `docs/reference/media-stack.md`
- `docs/reference/security-stack.md`

## Preferred Commands

- Windows: `.\haac.ps1 up`
- Linux/macOS: `sh ./haac.sh up`
- Global Task: `task up`

All three entrypoints run the same Task pipeline through the supported `haac` Cobra surface.

## Required `.env` Inputs

`task up` expects these `.env` surfaces to be populated before provisioning starts:

- infra and storage: `LXC_PASSWORD`, `LXC_MASTER_HOSTNAME`, `NAS_ADDRESS`, `HOST_NAS_PATH`, `NAS_PATH`, `NAS_SHARE_NAME`, `SMB_USER`, `SMB_PASSWORD`, `STORAGE_UID`, `STORAGE_GID`
- GitOps publication: `GITOPS_REPO_URL`, `GITOPS_REPO_REVISION`
- public routing: `DOMAIN_NAME`, `CLOUDFLARE_API_TOKEN`, `CLOUDFLARE_ACCOUNT_ID`, `CLOUDFLARE_ZONE_ID`, `CLOUDFLARE_TUNNEL_TOKEN`

`LXC_PASSWORD` is the documented password source of truth. The supported `haac` commands derive the effective Proxmox host password from it unless `PROXMOX_HOST_PASSWORD` is explicitly provided by the caller.

Proxmox access uses two related inputs:

- `MASTER_TARGET_NODE`: the Proxmox node name used by OpenTofu resources and generated inventory
- `PROXMOX_ACCESS_HOST`: optional workstation-reachable Proxmox API/SSH host; if unset, bootstrap falls back to `MASTER_TARGET_NODE`

## Preflight Contract

1. `.env` is present and complete.
2. `haac install-tools` has been run at least once through `.\haac.ps1` or `sh ./haac.sh`.
3. `haac check-env` confirms the effective Proxmox API and SSH host derived from `PROXMOX_ACCESS_HOST` with fallback to `MASTER_TARGET_NODE` is resolvable and reachable before provisioning starts.
4. `haac doctor` passes and confirms the local workstation toolchain.
5. `haac sync-repo` can fetch and merge the writable `origin/<GITOPS_REPO_REVISION>` branch before provisioning starts.

## Phase Contract

1. Preflight: `check-env`, `doctor`, `sync`
2. Infra provisioning: OpenTofu init and apply through the explicit `provision-infra` phase
3. Node configuration: Ansible plus K3s service recovery, local flannel `/run/flannel/subnet.env` readiness, and cluster node `Ready` gating before GitOps bootstrap
4. Secret and GitOps publication: regenerate rendered artifacts, push GitOps state, bootstrap ArgoCD
5. Staged readiness gates:
   - ArgoCD API reachability
   - `haac-platform`
   - `argocd`
   - `haac-workloads`
   - `haac-stack`
   - critical workload secret and downloader readiness
6. Cloudflare publication: tunnel ingress plus DNS reconciliation
7. Cluster verification
8. Public URL verification and final summary

## Rerun Contract

- `task up` is a convergent reconciliation command, not a one-shot bootstrap.
- Re-running after a partial failure is the primary supported recovery path for provisioning, configuration, GitOps, Cloudflare, and verification phases.
- If the rendered GitOps artifacts are unchanged, the publication phase should report convergence instead of creating an empty publish commit.
- If Cloudflare ingress rules and DNS records are already aligned, the publication phase should report reconciliation without creating duplicates.

## Failure And Retry Boundaries

The run stops immediately for:

- missing `.env` inputs
- missing local tooling
- missing or unreachable GitOps `origin` remote
- OpenTofu or Ansible command failures
- K3s node or flannel/CNI readiness failures during `Node configuration`
- ArgoCD application degradation
- Cloudflare API failures

The run retries until timeout for:

- Kubernetes API tunnel readiness
- ArgoCD sync and health transitions
- workload secret creation and downloader readiness
- public HTTP endpoint verification

When a retrying gate times out, the failure message should name the last gate reached so the next debugging step is obvious.

When any phase fails, the operator output should include:

- the failing phase
- the last verified phase
- whether rerunning `task up` is the normal recovery path or whether manual intervention is required first

## Expected Final Output

The last phase must print the public URL report derived from the Helm ingress source of truth in `k8s/charts/haac-stack/config-templates/values.yaml.template` and the generated `values.yaml`.

The table must include:

- service
- namespace
- auth mode
- status code
- URL

If some endpoints pass and others fail, the summary must still print every endpoint, report partial failure explicitly, and return a failing exit code.

## Known Recovery Pattern

- If infra already exists, resume from a narrower task instead of destroying everything.
- If the cluster tunnel path is broken, fix workstation-to-Proxmox reachability before retrying `up`.
- If the URL summary fails, inspect platform health before assuming workload-level failure.
