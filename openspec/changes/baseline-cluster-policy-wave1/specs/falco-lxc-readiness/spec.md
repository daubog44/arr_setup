## MODIFIED Requirements

### Requirement: Falco runtime is delivered through a supported host-side sensor path
The platform GitOps configuration MUST avoid deploying an unsupported Falco runtime DaemonSet onto the repository's unprivileged Proxmox LXC-based K3s nodes, while still keeping the Falco UI and alert pipeline healthy in-cluster.

#### Scenario: Enabled Falco includes repo-managed rule assets
- **WHEN** Falco is explicitly enabled through operator inputs
- **THEN** the supported host-side sensor path MUST consume the repo-managed homelab rule baseline required by this repository
- **AND** the cluster-side alert surface MUST remain compatible with those rules
