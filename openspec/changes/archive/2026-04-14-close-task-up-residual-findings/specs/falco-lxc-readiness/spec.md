## ADDED Requirements

### Requirement: Falco does not degrade platform health on unsupported unprivileged LXC nodes
The platform GitOps configuration MUST avoid deploying a permanently crash-looping Falco application onto the repository's unprivileged Proxmox LXC-based K3s nodes when the required probe-build prerequisites are not satisfied.

#### Scenario: Falco is skipped by default on unsupported LXC workers
- **GIVEN** the homelab uses the default unprivileged Proxmox LXC worker model
- **AND** Falco is not explicitly enabled through the operator inputs
- **WHEN** the platform GitOps manifests are rendered
- **THEN** the rendered Falco application manifest MUST become a clean no-op instead of an ArgoCD application that will crash-loop in-cluster

#### Scenario: Enabled Falco keeps the classic `ebpf` driver path documented
- **WHEN** Falco is explicitly enabled for a supported environment
- **THEN** the enabled manifest MUST avoid the failing `modern_ebpf` ring-buffer path observed on the live LXC nodes
