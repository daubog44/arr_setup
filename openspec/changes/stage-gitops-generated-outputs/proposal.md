## Why

The repo-managed secret generator writes some GitOps artifacts outside `k8s/charts/haac-stack/templates/secrets/`, notably `k8s/platform/argocd/install-overlay/argocd-oidc-sealed-secret.yaml` and `k8s/platform/chaos/litmus-admin-credentials-sealed-secret.yaml`.

Live evidence on April 17, 2026 showed the failure mode clearly:

- `python scripts/haac.py task-run -- up` regenerated the Litmus admin SealedSecret locally
- `push-changes` published only the staged subset under `SECRETS_DIR`, `values.yaml`, and a small render list
- ArgoCD then tried to apply the stale Litmus secret from Git and failed the platform root gate with `no key could decrypt secret`

That violates the GitOps publication contract: the repo can claim publication success while leaving generated platform artifacts unstaged and unpublished.

## What Changes

- Centralize the list of repo-managed generated GitOps outputs in `scripts/haac.py`.
- Reuse that same list from both `push-changes` and the pre-commit hook instead of hand-maintaining multiple partial staging lists.
- Add focused regression coverage for the staging list so future generated outputs are harder to forget.

## Capabilities

### New Capabilities
- `gitops-generated-output-staging`: the publication path stages every repo-managed generated GitOps artifact before commit/push.

### Modified Capabilities
- `task-up-bootstrap`: the bootstrap publication phase must not leave regenerated platform secrets local-only.

## Impact

- Affected code lives in `scripts/haac.py` and `tests/test_haac.py`.
- This changes publication behavior without changing the operator entrypoints.
