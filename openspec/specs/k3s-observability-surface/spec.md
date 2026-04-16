# k3s-observability-surface Specification

## Purpose
Define the repo-managed Prometheus and Grafana contract required for the official observability dashboards to stay usable on this K3s topology.

## Requirements
### Requirement: Official Grafana dashboards have a repo-managed K3s metrics surface

The repository MUST provide a K3s-compatible Prometheus metrics surface for the official Grafana dashboards it ships.

#### Scenario: Control-plane dashboards are rendered

- **WHEN** kube-prometheus-stack is reconciled on the HaaC K3s topology
- **THEN** the Prometheus configuration MUST expose the labels and targets required for the official Kubernetes API server dashboard
- **AND** the official dashboard variables MUST be able to resolve at least one `cluster` value and one `instance` value from the repo-managed metric surface
- **AND** the repo MUST NOT rely on undeclared kubeadm-only discovery behavior

### Requirement: Official observability verification detects empty dashboards

The operator contract MUST distinguish between a reachable Grafana login and a usable official observability surface.

#### Scenario: Final observability verification runs

- **WHEN** the operator verifies the official Grafana UI
- **THEN** the check MUST fail if the configured official dashboards or datasource selectors resolve to empty or broken data for the supported cluster topology
