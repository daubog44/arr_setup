# Why

The public auth surface is now converged, but Semaphore still holds the most dangerous remaining bootstrap credential path:

- the bootstrap playbook authorizes `haac*.pub` broadly on Proxmox root and guest root accounts
- the cluster still publishes `haac-ssh-key`, which mounts a private key into `mgmt`
- Semaphore uses that same key both for host access and for repository access
- the maintenance inventory still assumes root logins to guests and the Proxmox host

That means a compromise of the Semaphore namespace or the mounted key remains an indirect root compromise of the infrastructure.

## What Changes

- introduce an explicit three-role SSH model:
  - operator bootstrap key
  - repo deploy key
  - Semaphore maintenance key
- stop authorizing `haac*.pub` via wildcard loops on Proxmox root and guest root accounts
- create a dedicated non-root maintenance principal on Proxmox and guests for Semaphore-driven maintenance
- move Semaphore maintenance automation to a dedicated maintenance inventory that uses `become`
- restrict the maintenance principal to a narrow repo-managed sudo surface instead of direct root SSH
- stop reusing the infrastructure maintenance key for Git repository access
- keep the current operator bootstrap path working for `task up`

## Expected Outcome

- `task up` still provisions and bootstraps the homelab with the operator key path
- Semaphore keeps infrastructure maintenance access, but the cluster-held private key is no longer root-equivalent
- guest and Proxmox root accounts no longer accumulate every `haac*.pub` key
- repository access and infrastructure access no longer share a credential
- the maintenance playbook remains rerunnable through Semaphore with a bounded, documented privilege model
