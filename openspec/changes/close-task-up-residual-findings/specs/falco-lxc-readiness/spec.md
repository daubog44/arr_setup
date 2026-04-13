## ADDED Requirements

### Requirement: Falco uses a supported syscall driver on unprivileged LXC K3s nodes
The platform GitOps configuration MUST select a Falco syscall driver that converges on the repository's unprivileged Proxmox LXC-based K3s nodes without relying on an undocumented host-wide BPF sysctl downgrade.

#### Scenario: LXC-compatible Falco driver is configured
- **WHEN** the Falco platform application is rendered for this homelab stack
- **THEN** the selected driver MUST avoid the failing `modern_ebpf` ring-buffer path observed on the live LXC nodes

#### Scenario: Falco becomes healthy after reconciliation
- **WHEN** the Falco application syncs on the cluster
- **THEN** the Falco DaemonSet pods MUST stop crash-looping on the monitored nodes

