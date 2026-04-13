## 1. Implementation

- [ ] 1.1 Align the Semaphore ArgoCD Application values with the official chart `16.0.11` schema and move public auth to Traefik/Authelia middleware
- [ ] 1.2 Extend the generated Semaphore secret contract with the admin metadata keys required by the official chart without duplicating the admin password into tracked manifests
- [ ] 1.3 Convert `semaphore-bootstrap` from a Helm hook to a rerunnable Argo-managed Job and keep its bootstrap path idempotent
- [ ] 1.4 Regenerate the rendered GitOps outputs affected by the Semaphore Application and secret contract changes

## 2. Validation

- [ ] 2.1 Validate with `openspec validate stabilize-semaphore-bootstrap-readiness`
- [ ] 2.2 Validate with `helm template haac-stack k8s/charts/haac-stack`
- [ ] 2.3 Validate the bootstrap contract locally with `python scripts/haac.py check-env` and `python scripts/haac.py task-run -- -n up`
- [ ] 2.4 Publish the GitOps revision and rerun `python scripts/haac.py wait-for-stack ...` until it either passes the Semaphore gate or fails on a later concrete blocker
