## 1. Implementation

- [ ] 1.1 Correct the Trivy Operator chart values so namespace scoping uses the supported top-level keys
- [ ] 1.2 Reduce the default scan scope and concurrency to a control-plane-safe profile for this homelab
- [ ] 1.3 Move Trivy Operator later in platform sync ordering

## 2. Validation

- [ ] 2.1 Validate with `openspec validate stabilize-k3s-control-plane-load`
- [ ] 2.2 Validate with `kubectl kustomize k8s/platform`, `helm template haac-stack k8s/charts/haac-stack`, and `python scripts/haac.py task-run -- -n up`
- [ ] 2.3 Rerun the live bootstrap and record the furthest verified phase together with the control-plane outcome
