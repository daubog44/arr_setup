## 1. Implementation

- [ ] 1.1 Publish the repo-local ArgoCD install overlay and point the `argocd` Application at it through the rendered manifest/template path
- [ ] 1.2 Keep the imperative repo-server bootstrap patch seed aligned with the declarative overlay path
- [ ] 1.3 Add explicit platform sync ordering so `kube-prometheus-stack` lands before `node-problem-detector` and `trivy-operator`
- [ ] 1.4 Add the sync option needed to tolerate transient missing `ServiceMonitor` CRDs during first bootstrap

## 2. Validation

- [ ] 2.1 Validate with `kubectl kustomize k8s/platform/argocd/install-overlay`
- [ ] 2.2 Validate with `openspec validate stabilize-platform-gitops-readiness`
- [ ] 2.3 Publish the GitOps changes and verify that `python scripts/haac.py wait-for-stack ...` moves past `haac-platform`
