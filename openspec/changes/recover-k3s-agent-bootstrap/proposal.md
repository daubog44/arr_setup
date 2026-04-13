## Why

`task up` can recreate worker LXCs while leaving the local OpenTofu and Ansible history in a partially converged state. In that case the worker may already contain `/usr/local/bin/k3s`, but still be missing the active `k3s-agent` service/runtime state and the generated `/var/lib/rancher/k3s/agent/etc/containerd/config.toml`. The current playbook treats the binary as sufficient proof of installation, skips the install/start path, and then times out waiting for a file that never appears.

## What Changes

- Make worker bootstrap detect incomplete K3s agent state instead of keying only on the binary.
- Ensure `configure-os` starts or reinstalls the K3s agent when the service unit or runtime state is missing.
- Move the NVIDIA runtime wait gate behind the recovery/start path so recreated workers can converge again.

## Impact

- `ansible/playbook.yml`
- `task configure-os`
- `task up`
