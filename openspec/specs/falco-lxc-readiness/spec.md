# falco-lxc-readiness Specification

## Purpose
Keep the Falco public surface healthy while delivering supported runtime coverage in this homelab environment.
## Requirements
### Requirement: Falco runtime is delivered through a supported host-side sensor path
The platform GitOps configuration MUST avoid deploying an unsupported Falco runtime DaemonSet onto the repository's unprivileged Proxmox LXC-based K3s nodes, while still keeping the Falco UI and alert pipeline healthy in-cluster.

#### Scenario: Falco is skipped cleanly when disabled
- **GIVEN** the homelab uses the default unprivileged Proxmox LXC worker model
- **AND** Falco is not explicitly enabled through the operator inputs
- **WHEN** the platform GitOps manifests are rendered
- **THEN** the rendered Falco application manifest MUST become a clean no-op instead of an ArgoCD application that will crash-loop in-cluster

#### Scenario: Enabled Falco deploys only the cluster-side alert surface
- **WHEN** Falco is explicitly enabled for this environment
- **THEN** the enabled manifest MUST render a healthy cluster-side `falcosidekick` application
- **AND** the platform layer MUST provide a stable in-cluster UI service plus a stable internal ingest endpoint for host-side Falco events
- **AND** it MUST NOT render an in-cluster Falco DaemonSet for the unprivileged LXC workers

#### Scenario: Enabled Falco configures a supported host-side sensor
- **WHEN** Falco is explicitly enabled through operator inputs
- **THEN** the Proxmox host configuration MUST install and enable a Falco sensor using the supported `modern_ebpf` host path
- **AND** that sensor MUST forward events to the cluster-side ingest endpoint through `http_output`

#### Scenario: Falco enablement no longer depends on worker runtime labels
- **WHEN** Falco is enabled through operator inputs
- **THEN** the repo MUST NOT require `WORKER_NODES_JSON` entries with `haac.io/falco-runtime=true`
- **AND** bootstrap validation MUST derive Falco readiness from the host-side sensor path instead of an undocumented manual cluster label

