## Why

The current GitOps readiness gate can report success while ArgoCD is still synced to an older Git revision than the one just pushed by the operator flow. In the live cluster on April 17, 2026, `haac-root` remained at `05a3b8e13e1abffcfe0977957161ee465ffdaa63` and `haac-platform` remained at `7612105f502194c68994b28d0cac1cd23c02fd02` even though local and remote `main` had already advanced to `d831d4d26cb2143956dfb3fb682c835fc8e94cc7`. `wait-for-argocd-sync` still passed because it only required `Synced` plus `Healthy`, not freshness against the expected GitOps revision.

That stale-success path directly breaks the `task up` contract: later verification can fail against old manifests while the bootstrap ladder claims GitOps readiness already succeeded.

## What Changes

- Make the ArgoCD readiness gate compare repo-managed application sync revisions against the expected GitOps commit, not only `Synced` and `Healthy`.
- Force a hard refresh for stale repo-managed applications during bootstrap/reconcile so ArgoCD re-resolves the branch head it should be applying, even when the stale application is currently degraded or failed on an older revision.
- Record the revision-freshness contract in OpenSpec so future loop rounds cannot treat stale GitOps state as healthy convergence.

## Capabilities

### New Capabilities

- `argocd-head-revision-readiness`: repo-managed ArgoCD applications only satisfy bootstrap readiness after they converge to the expected GitOps commit.

### Modified Capabilities

- `task-up-bootstrap`: GitOps readiness must prove freshness against the published repo revision, not just health against an older commit.

## Impact

- Affected code lives primarily in `scripts/haac.py` and focused regression coverage in `tests/test_haac.py`.
- This change improves correctness of `task up`, `task reconcile:argocd`, and any loop round that depends on ArgoCD freshness before browser verification.
