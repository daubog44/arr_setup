## ADDED Requirements

### Requirement: Repo-managed services expose usable Grafana metrics surfaces

The repository MUST make Grafana a usable operator surface for the repo-managed platform services it advertises.

#### Scenario: Service dashboards are provisioned

- **WHEN** Grafana provisions repo-managed service dashboards
- **THEN** the required Prometheus scrape targets for those services MUST exist in the repo-managed cluster manifests
- **AND** the shipped dashboards MUST query metric families that the repo-managed service configuration actually produces

### Requirement: Service dashboard verification detects empty service observability

The operator verification surface MUST fail when a shipped service dashboard loads but still resolves empty because the repo-managed metrics surface is incomplete.

#### Scenario: Trivy or Argo CD dashboard verification runs

- **WHEN** final Grafana verification checks a shipped service dashboard
- **THEN** the check MUST fail if the required service metrics are absent from Prometheus
- **AND** the check MUST fail if the browser reaches the dashboard shell but the service panels still resolve to empty or broken data
