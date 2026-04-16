# maintenance-job-boundaries Specification

## Purpose
Keep recurring work on the correct execution surface so cluster-local automation stays inside Kubernetes and infrastructure maintenance stays in Semaphore-driven Ansible workflows.
## Requirements
### Requirement: Cluster-local recurring work uses Kubernetes CronJobs

Recurring work that only needs in-cluster APIs, service accounts, and persistent volumes MUST be scheduled as Kubernetes CronJobs.

#### Scenario: In-cluster recurring work is declared

- **WHEN** the recurring task only needs Kubernetes-native access and should run next to the managed workloads
- **THEN** the repository MUST model it as a Kubernetes CronJob
- **AND** it MUST NOT require Semaphore inventory, jump-host access, or maintenance SSH credentials

### Requirement: Infrastructure maintenance stays in Semaphore schedules

Recurring work that needs host inventory, serialized maintenance, jump-host access, or bounded sudo on Proxmox or the K3s nodes MUST stay in Semaphore schedules backed by the maintenance playbooks.

#### Scenario: Host-level maintenance is declared

- **WHEN** the recurring task needs Proxmox access, guest SSH, rolling host updates, or reboot-aware maintenance semantics
- **THEN** the repository MUST model it as a Semaphore schedule
- **AND** it MUST use the maintenance inventory and bounded maintenance playbooks instead of a Kubernetes CronJob
