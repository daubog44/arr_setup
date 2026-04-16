# falco-lxc-readiness Specification

## Purpose
TBD - created by archiving change close-task-up-residual-findings. Update Purpose after archive.
## Requirements
### Requirement: Falco does not degrade platform health on unsupported unprivileged LXC nodes
The platform GitOps configuration MUST avoid deploying a permanently crash-looping Falco application onto the repository's unprivileged Proxmox LXC-based K3s nodes when the required `modern_ebpf` prerequisites are not satisfied.

#### Scenario: Falco is skipped by default on unsupported LXC workers
- **GIVEN** the homelab uses the default unprivileged Proxmox LXC worker model
- **AND** Falco is not explicitly enabled through the operator inputs
- **WHEN** the platform GitOps manifests are rendered
- **THEN** the rendered Falco application manifest MUST become a clean no-op instead of an ArgoCD application that will crash-loop in-cluster

#### Scenario: Enabled Falco keeps the compatible `modern_ebpf` driver path documented
- **WHEN** Falco is explicitly enabled for a supported environment
- **THEN** the enabled manifest MUST render the supported `modern_ebpf` driver path
- **AND** the stable documentation MUST describe the required host `/usr/lib/modules`, `/usr/src`, and `/sys/kernel/*` exposure on the declared runtime-capable workers
