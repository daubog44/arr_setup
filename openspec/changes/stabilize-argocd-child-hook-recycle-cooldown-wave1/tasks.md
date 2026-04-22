## 1. Implementation

- [x] 1.1 Add a bounded cooldown to the repo-managed ArgoCD missing-hook recycle path
- [x] 1.2 Add regression tests covering the cooldown and the existing recycle behavior

## 2. Validation

- [x] 2.1 Validate the OpenSpec change and targeted unit tests
- [x] 2.2 Re-run the cold-cycle wrapper acceptance path and confirm `kyverno` no longer fails in the child recycle loop
