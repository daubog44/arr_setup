## 1. Metrics surface

- [x] 1.1 Add repo-managed Prometheus scrape coverage for Argo CD metrics services
- [x] 1.2 Align the Trivy operator scanner configuration with the shipped Grafana dashboard expectations

## 2. Dashboard surface

- [x] 2.1 Provision Grafana dashboards for the repo-managed service metrics surface starting with Argo CD and Kyverno
- [x] 2.2 Tighten verification so empty Trivy and Argo CD dashboards fail the operator contract

## 3. Verification

- [x] 3.1 Validate with OpenSpec, local renders, live reconcile, and browser checks
