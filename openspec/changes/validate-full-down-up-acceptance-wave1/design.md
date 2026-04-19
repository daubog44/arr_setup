## Design

### Scope boundary

This wave is acceptance-first. It should avoid code changes unless the `down` or `up` cycle reveals a concrete defect.

### Acceptance contract

The required lifecycle is:

1. verify the repo is checkpointed and the cluster is in a known-good state
2. run `task down`
3. run `task up`
4. wait for ArgoCD health and public surface verification
5. rerun the media verifier and browser checks

Any failure found during the cycle should either:

- become the direct implementation work of this wave if the fix is narrow and obvious, or
- become a new evidence-backed OpenSpec change if the defect is broader

### Verification

- `openspec validate validate-full-down-up-acceptance-wave1`
- a real `task down`
- a real `task up`
- post-bootstrap `wait-for-argocd-sync`
- post-bootstrap browser verification and ARR verifier

### Recovery and rollback

- if `task down` succeeds and `task up` fails, rerunning `task up` remains the supported recovery path unless the failure output says otherwise
