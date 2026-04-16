## Design

### Evidence

The current Grafana public UI is reachable, but the shipped Kubernetes API server dashboard reports `No data`. Live inspection shows the Prometheus scrape target for `job="apiserver"` is present, yet the official dashboard variables still resolve empty because the repo-managed Prometheus config does not stamp a stable `cluster` label onto the metric surface expected by the shipped dashboards.

### Solution shape

This wave will add a narrow K3s observability layer:

- repo-managed Prometheus labels and values that make the shipped control-plane dashboards resolve correctly on this topology
- explicit Grafana datasource and dashboard provisioning so the official dashboards do not depend on upstream implicit defaults
- cleanup of kube-prometheus-stack values that currently carry dead or misleading configuration
- browser/runtime verification that fails when the official Grafana dashboards are empty or their datasource variables cannot resolve

### Verification

- `openspec validate restore-k3s-observability-surface`
- `python scripts/haac.py task-run -- -n up`
- `& .\.tools\windows-amd64\bin\helm.exe template haac-stack k8s\charts\haac-stack`
- `& .\.tools\windows-amd64\bin\kubectl.exe kustomize k8s\platform`
- browser verification for Grafana after reconciliation when cluster access is available
