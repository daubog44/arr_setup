## 1. Spec And Backlog Hygiene

- [ ] 1.1 Sync the accepted public-surface and bootstrap-governance requirements into stable specs
- [ ] 1.2 Audit the remaining in-progress bootstrap changes and archive the ones already satisfied or superseded by stable behavior

## 2. Public Surface And Auth

- [ ] 2.1 Extend the official route catalog so it can express route enablement and full Homepage metadata
- [ ] 2.2 Publish Litmus and conditional Falco routes through that catalog and make Homepage render them
- [ ] 2.3 Make Authelia forward-auth the default protection posture for official app UIs, with explicit public opt-out only where required
- [ ] 2.4 Update endpoint verification to report the real protected/public posture from the same catalog

## 3. Validation

- [ ] 3.1 Validate with `openspec validate stabilize-public-surface-and-spec-governance`, `helm template`, `kubectl kustomize`, and `python -m py_compile`
- [ ] 3.2 Reconcile the GitOps state and rerun `task verify-endpoints`
- [ ] 3.3 Rerun `task up` when the environment is available and record the furthest verified phase plus the final official UI URLs
