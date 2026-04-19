## 1. Kyverno topology

- [x] 1.1 Update the repo-managed Kyverno Helm values so the admission controller runs with two replicas
- [x] 1.2 Add spread or disruption settings that keep at least one Kyverno admission endpoint available during ordinary restarts

## 2. Validation

- [x] 2.1 Validate the OpenSpec change and any touched static render paths
- [x] 2.2 Validate live by reconciling Kyverno and rerunning the ArgoCD readiness gate
