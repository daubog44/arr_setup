## Design

### Evidence

- Prometheus query `count(up{namespace="argocd"})` returned an empty result, so Argo CD metrics are not part of the current scrape surface.
- Prometheus query `count(up{namespace="kyverno"})` returned `4`, so Kyverno already has a valid metrics surface.
- Prometheus query `sum(trivy_image_vulnerabilities)` returned data, while `sum(trivy_resource_configaudits)`, `sum(trivy_clusterrole_clusterrbacassessments)`, and `sum(trivy_image_exposedsecrets)` returned empty results.
- Grafana dashboard `ycwPj724k` ("Trivy Operator Dashboard") queries those missing Trivy metric families, so the dashboard is structurally incompatible with the current repo-managed Trivy scanner settings.

### Solution shape

- Add repo-managed `ServiceMonitor`s for the Argo CD metrics services that are already exposed by the upstream install overlay.
- Import or provision a Grafana dashboard for Argo CD that uses the Prometheus datasource.
- Align Trivy operator scanner flags with the shipped dashboard by enabling the missing scanners in a bounded homelab-safe configuration.
- Import a Grafana dashboard for Kyverno because its metrics surface is already present and scrapeable.
- Enable Alloy self-monitoring in Prometheus and provision a repo-managed Grafana dashboard for the collector itself.
- Extend the Grafana verification path so at least the Trivy and Argo CD service dashboards must show data, not only load.

### Verification

- `openspec validate centralize-service-observability-surface`
- `& .\.tools\windows-amd64\bin\kubectl.exe kustomize k8s\platform`
- `python scripts/haac.py task-run -- wait-for-argocd-sync`
- `node scripts/verify-public-auth.mjs`
- browser verification for Grafana service dashboards
