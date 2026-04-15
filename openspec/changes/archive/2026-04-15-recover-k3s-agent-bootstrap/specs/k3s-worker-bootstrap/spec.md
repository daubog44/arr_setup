## ADDED Requirements

### Requirement: K3s worker bootstrap tolerates partial agent installs
The worker-node bootstrap MUST recover when a recreated or partially configured worker already contains the `k3s` binary but is still missing the active agent service/runtime state required for cluster join.

#### Scenario: Binary exists but runtime state is missing
- **GIVEN** a K3s worker where `/usr/local/bin/k3s` exists
- **AND** the worker is missing `/var/lib/rancher/k3s/agent/etc/containerd/config.toml` or the effective `k3s-agent` service state required to generate it
- **WHEN** `task configure-os` or the worker setup play runs
- **THEN** the playbook MUST rerun or restart the K3s agent path instead of treating the worker as already converged
- **AND** the worker MUST continue toward cluster join instead of timing out waiting for `config.toml`
