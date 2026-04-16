## ADDED Requirements

### Requirement: Recurring jobs use the execution plane that matches their trust and runtime boundary
The system MUST keep recurring work in the execution plane that matches where the work runs and what credentials it needs.

#### Scenario: In-cluster recurring work is rendered
- **WHEN** recurring work executes only against cluster-local services or namespaces
- **THEN** it MUST be modeled as a Kubernetes CronJob
- **AND** it MUST NOT require Semaphore just to run a cluster-local command on a schedule

#### Scenario: Infra maintenance is rendered
- **WHEN** recurring work requires Ansible inventory, jump-host access, maintenance credentials, serialized host rollout, or host reboot semantics
- **THEN** it MUST be modeled as a Semaphore schedule and template
- **AND** it MUST NOT be moved into a Kubernetes CronJob only for uniformity

### Requirement: The current recurring-job split is documented and reviewable
The repository MUST document which recurring jobs intentionally live in Kubernetes and which intentionally live in Semaphore.

#### Scenario: Operator reads the architecture or bootstrap docs
- **WHEN** the operator inspects recurring maintenance behavior
- **THEN** the repo MUST identify the current Kubernetes CronJobs and the current Semaphore schedules
- **AND** it MUST explain the ownership boundary between those two planes
