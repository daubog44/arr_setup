## Why

Grafana is now usable for the control-plane surface, but the service-level observability layer is still fragmented. On April 17, 2026:

- `argocd_up` returned an empty result in Prometheus even though Argo CD metrics services exist in-cluster.
- `kyverno_up` returned data, proving some platform services are already scrapeable.
- Trivy metrics exposed only `trivy_image_vulnerabilities` and `trivy_cluster_compliance`, while the shipped Trivy dashboard also queries `trivy_resource_configaudits`, `trivy_clusterrole_clusterrbacassessments`, and `trivy_image_exposedsecrets`.

This leaves Grafana with dashboards that are reachable but not trustworthy as the central operator UI.

## What Changes

- Add the missing Prometheus scrape surface for service metrics that are already exposed but not yet collected.
- Align the repo-managed Trivy operator configuration with the shipped Grafana dashboard, or replace the dashboard if the repo intentionally keeps scanners disabled.
- Provision a first-class Grafana dashboard surface for repo-managed services that already emit useful metrics, including Alloy self-monitoring.
- Extend verification so browser/runtime checks fail when those official service dashboards are still empty.

## Capabilities

### New Capabilities

- `service-observability-surface`: repo-managed service metrics, dashboards, and verification for the platform services that operators are expected to inspect in Grafana.

## Impact

- Expected changes live under `k8s/platform/applications/`, possible supporting manifests under `k8s/platform/`, and Grafana verification scripts.
- This change improves Grafana as the central operator surface without changing the public hostname contract.
