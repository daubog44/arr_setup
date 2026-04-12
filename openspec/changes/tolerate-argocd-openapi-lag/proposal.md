## Why

`configure-os` now progresses past the corrected K3s networking gates, Sealed Secrets rollout, and namespace bootstrap, but it still fails on the ArgoCD install step.

The concrete failure is:

- `k3s kubectl apply -n argocd --server-side --force-conflicts -f https://raw.githubusercontent.com/argoproj/argo-cd/v3.3.2/manifests/install.yaml`
- `error validating data: failed to download openapi: the server is currently unable to handle the request`

That means bootstrap is blocked by client-side schema validation timing, not by the ArgoCD manifest itself.

## What Changes

- make the ArgoCD bootstrap apply tolerant to temporary OpenAPI unavailability on the API server
- preserve server-side apply and conflict forcing while disabling only the client-side validation dependency that is failing
- verify `configure-os` progresses beyond ArgoCD install after this change

## Impact

- `task up` becomes more resilient during bootstrap on a recovering cluster
- ArgoCD install no longer depends on the API server serving OpenAPI perfectly at that exact moment
- the new failure surface, if any, should move to a later and more actionable bootstrap phase
