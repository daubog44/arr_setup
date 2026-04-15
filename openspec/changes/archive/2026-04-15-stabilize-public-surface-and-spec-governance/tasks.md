## 1. Spec And Backlog Hygiene

- [x] 1.1 Sync the accepted public-surface and bootstrap-governance requirements into stable specs
- [x] 1.2 Audit the remaining in-progress bootstrap changes and archive the ones already satisfied or superseded by stable behavior

## 2. Public Surface And Auth

- [x] 2.1 Extend the official route catalog so it can express route enablement and full Homepage metadata
- [x] 2.2 Publish Litmus and conditional Falco routes through that catalog and make Homepage render them
- [x] 2.3 Make Authelia forward-auth the default protection posture for official app UIs, with explicit public opt-out only where required
- [x] 2.4 Update endpoint verification to report the real protected/public posture from the same catalog

## 3. Validation

- [x] 3.1 Validate with `openspec validate stabilize-public-surface-and-spec-governance`, `helm template`, `kubectl kustomize`, and `python -m py_compile`
- [x] 3.2 Reconcile the GitOps state and rerun `task verify-endpoints`
- [x] 3.3 Rerun `task up` when the environment is available and record the furthest verified phase plus the final official UI URLs
