## MODIFIED Requirements

### Requirement: Falco does not degrade platform health on unsupported unprivileged LXC nodes
The platform GitOps configuration MUST avoid deploying a permanently crash-looping Falco runtime onto the repository's unprivileged Proxmox LXC-based K3s nodes, while still supporting runtime coverage on explicitly declared compatible workers.

#### Scenario: Falco is skipped by default on unsupported LXC workers
- **GIVEN** the homelab uses the default unprivileged Proxmox LXC worker model
- **AND** Falco is not explicitly enabled through the operator inputs
- **WHEN** the platform GitOps manifests are rendered
- **THEN** the rendered Falco application manifest MUST become a clean no-op instead of an ArgoCD application that will crash-loop in-cluster

#### Scenario: Enabled Falco uses the compatible `ebpf` driver path
- **WHEN** Falco is explicitly enabled for this environment
- **THEN** the enabled manifest MUST avoid the failing `modern_ebpf` ring-buffer path observed on the live LXC nodes
- **AND** it MUST render the upstream-supported `ebpf` driver path instead

#### Scenario: Enabled Falco requires at least one repo-managed runtime node
- **WHEN** Falco is explicitly enabled through operator inputs
- **THEN** the repo MUST require at least one worker to be declared runtime-capable through source-of-truth node labels
- **AND** the operator workflow MUST fail closed if Falco is enabled without any declared runtime-capable worker

#### Scenario: Enabled Falco schedules only onto declared runtime-capable workers
- **WHEN** Falco is enabled and the runtime-capable worker set is declared
- **THEN** the Falco daemonset MUST schedule only onto those declared workers
- **AND** the node-selection mechanism MUST derive from repo-managed operator inputs rather than an undocumented manual cluster label
