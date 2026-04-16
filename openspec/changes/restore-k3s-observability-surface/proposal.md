## Why

Grafana currently renders official dashboards that are visually reachable but operationally empty. The current kube-prometheus-stack configuration does not yet define a repo-managed K3s-compatible observability surface for API server and related control-plane metrics, so the public observability UI looks healthy while the most important dashboards show no data.

## What Changes

- Add a repo-managed K3s observability surface for the control plane metrics needed by the shipped Grafana dashboards.
- Reconcile Grafana datasource and dashboard expectations with the metrics that actually exist on this cluster topology.
- Add verification that catches an empty official Grafana surface instead of treating login success as sufficient.

## Capabilities

### New Capabilities
- `k3s-observability-surface`: repo-managed Prometheus scrape targets and Grafana readiness checks for the K3s control plane and official dashboards.

### Modified Capabilities
- `task-up-bootstrap`: final verification for the official observability UI must distinguish between reachable Grafana login and usable dashboard data.

## Impact

- Affected code will primarily live under `k8s/platform/applications/`, possible supporting manifests in `k8s/platform/`, and browser verification paths.
- This change is expected to touch Grafana/Prometheus render logic but not the public hostname contract.
