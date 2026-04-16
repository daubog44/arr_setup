# Design

## Scope

This change hardens Semaphore's infrastructure access path without removing its ability to run the repo maintenance playbooks. It does not yet redesign Cloudflare publication or the broader bootstrap modularization work.

## Credential roles

### Operator bootstrap key

- remains the workstation/operator key used by `task up`
- continues to reach Proxmox and guest root during bootstrap and recovery
- is the only key that OpenTofu and the main bootstrap inventory rely on

### Repo deploy key

- becomes a distinct optional keypair
- is never authorized on Proxmox or guest hosts
- is used only for Semaphore repository access when the configured GitOps URL requires SSH auth
- is not mounted into the cluster for the current public-HTTPS repo path

### Semaphore maintenance key

- remains the only private key mounted into the cluster for Semaphore-driven maintenance
- is authorized only for a dedicated maintenance principal on Proxmox and the guests
- must not be present in root `authorized_keys`

## Maintenance principal

The repo introduces one explicit maintenance principal, defaulting to `haac-maint`.

Properties:

- local account on Proxmox and all K3s nodes
- SSH login allowed only with the Semaphore maintenance public key
- shell access allowed, but root escalation must go through `sudo`
- `sudo` is restricted to repo-managed maintenance wrapper commands instead of unrestricted root shells

## Maintenance command boundary

Instead of allowing broad root-like Ansible module execution, the repo installs repo-managed wrapper scripts:

- one wrapper for K3s guest maintenance
- one wrapper for Proxmox host maintenance

The maintenance playbook calls those wrappers with `become: true`. The maintenance sudoers policy only allows those wrappers.

This keeps Semaphore maintenance functional while materially reducing the blast radius of the cluster-held private key.

## Inventory split

The repo keeps two inventories:

- bootstrap inventory: root/operator path for `task up`
- maintenance inventory: maintenance principal plus `become`

Semaphore bootstrap must register the maintenance inventory, not the bootstrap inventory.

## Repository auth split

Semaphore repository creation must no longer reuse the maintenance SSH key.

- when `GITOPS_REPO_URL` is public HTTPS, Semaphore must create the repository without an SSH key
- when the URL requires SSH auth, Semaphore must use the dedicated repo deploy key instead

## Verification

The change is only done when:

- OpenSpec validates
- Helm and Kustomize renders still pass
- `task -n up` still passes
- the generated maintenance inventory uses the maintenance principal and `become`
- the Semaphore bootstrap manifest mounts only the maintenance key for infrastructure access
- the Proxmox and guest root authorization logic no longer uses wildcard `haac*.pub`
- the cluster-held Semaphore maintenance key is no longer authorized for direct root SSH on Proxmox or the guests
