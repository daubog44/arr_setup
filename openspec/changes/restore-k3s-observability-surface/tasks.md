## 1. Metrics surface

- [x] 1.1 Add a repo-managed K3s-compatible scrape surface for the control-plane metrics needed by the official Grafana dashboards
- [x] 1.2 Reconcile kube-prometheus-stack values with the actual K3s topology instead of assuming generic kubeadm-style discovery
- [x] 1.3 Add or adjust the stable observability spec

## 2. Verification

- [x] 2.1 Tighten Grafana verification so empty official dashboards fail the operator contract
- [x] 2.2 Validate with OpenSpec, Helm, Kustomize, dry-run bootstrap, and browser checks when the cluster is reachable
