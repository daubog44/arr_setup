## Design

### 1. Align the Semaphore Application with chart `16.0.11`

The current Application values still use the old key layout:

- `semaphore.access_key_encryption`
- `semaphore.admin`
- `semaphore.oidcProviders`

The official chart for `16.0.11` expects:

- `database.*`
- `admin.*`
- `oidc.*`
- `secrets.*`

Because the repo uses the wrong keys, the chart silently falls back to its defaults and the live Deployment runs with `SEMAPHORE_DB_DIALECT=bolt`. The Application must be updated to the official schema so the rendered Deployment matches the intended PostgreSQL plus local-admin bootstrap model.

### 2. Keep public auth at Traefik/Authelia

The chart no longer supports the repo's old `existingSecret` shape for OIDC provider secrets. The smallest safe fix is:

- keep local admin login enabled on the in-cluster service
- disable chart-level OIDC for Semaphore
- protect the public Traefik `IngressRoute` with the existing `force-https` and `authelia` middlewares in `mgmt`

That preserves public protection without embedding the OIDC client secret into tracked GitOps manifests.

### 3. Extend the sealed-secret contract for chart-managed admin creation

The official chart's admin init container reads all admin fields from one secret. The generated `semaphore-db-secret` currently contains only:

- `POSTGRES_PASSWORD`
- `APP_SECRET`
- `OIDC_SECRET`
- `ADMIN_PASSWORD`

The generator must also provide the admin metadata keys required by the chart:

- `ADMIN_USERNAME`
- `ADMIN_EMAIL`
- `ADMIN_NAME`

These can use operator defaults when not explicitly provided in `.env`, while the password remains sourced from `.env`.

### 4. Remove Helm hook semantics from `semaphore-bootstrap`

`semaphore-bootstrap` currently uses `helm.sh/hook` annotations. Under ArgoCD this keeps the application operation stuck on `waiting for completion of hook batch/Job/semaphore-bootstrap` even when the underlying pod is gone or the chart contract changed.

The Job should instead:

- remain a normal rendered resource
- keep the existing sync wave
- add `argocd.argoproj.io/sync-options: Force=true,Replace=true`

That makes it rerunnable without hook-state drift and lets ArgoCD evaluate the Job as a normal resource.

### 5. Preserve idempotence

The bootstrap Job already checks for the target project before creating resources. That logic should stay, but the login path must use the chart-compatible local admin created from the corrected secret contract.

### 6. Validation

Validation for this change is:

- `openspec validate stabilize-semaphore-bootstrap-readiness`
- `helm template haac-stack k8s/charts/haac-stack`
- `python scripts/haac.py check-env`
- `python scripts/haac.py task-run -- -n up`
- publish the GitOps revision
- rerun `python scripts/haac.py wait-for-stack ...` until it moves beyond `semaphore-bootstrap` or fails later on a new concrete gate
