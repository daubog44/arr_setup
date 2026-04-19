## Why

Live validation on April 19, 2026 showed that the ARR/bootstrap failures were being driven by infrastructure identity drift rather than by ArgoCD or the media apps themselves.

On the Proxmox host, the declared worker containers in OpenTofu state are `101` and `102`, but additional running LXCs `104` and `105` reuse the same hostnames and IPv4 addresses as the managed workers. The resulting `k3s-agent` logs show `Node password rejected, duplicate hostname or contents of '/etc/rancher/node/password' may not match server node-passwd entry`, while ArgoCD, `kubectl exec`, and Kyverno all flap behind intermittent worker readiness.

## What Changes

- Add a repo-managed node identity drift repair path that inspects the declared LXC VMIDs from OpenTofu state, compares them against live Proxmox LXC configs, and detects unmanaged containers that duplicate the hostname or IP of a declared K3s node.
- Quarantine unmanaged duplicate LXC workers safely by disabling `onboot` and stopping them, instead of deleting them blindly.
- Run that quarantine step automatically before the Ansible `configure-os` phase so `task up` and `task configure-os` recover without manual Proxmox forensics.
- Surface explicit operator output when duplicate node identities are detected and quarantined.

## Capabilities

### New Capabilities
- `k3s-node-identity-drift`: Detect and safely quarantine unmanaged Proxmox LXC nodes that duplicate the identity of declared K3s nodes.

### Modified Capabilities
- `task-up-idempotence`: The supported rerun path must recover duplicate unmanaged node identities before node configuration continues.

## Impact

- Affected code will primarily live in `scripts/haac.py`, `tests/test_haac.py`, and the bootstrap docs/runbooks.
- Live validation must include OpenSpec validation, focused unit coverage, a repair/quarantine run against the current Proxmox surface, a `configure-os` rerun, and downstream GitOps/media verification once worker stability returns.
