## 1. Semaphore Post-Install Catalog

- [x] 1.1 Extract Semaphore bootstrap logic and maintenance definitions into dedicated repo-managed files mounted into the post-install Job
- [x] 1.2 Reconcile Semaphore schedules with stable names and `active: true` instead of the currently ineffective payload shape
- [x] 1.3 Validate the rendered Job and confirm the managed project/template/schedule contract still matches the live Semaphore API

## 2. Homepage Operator Surface

- [x] 2.1 Replace broken Homepage icon metadata with supported Homepage icon identifiers from the official ingress catalog
- [x] 2.2 Extend the route catalog helper logic to render optional widget metadata from the official ingress catalog
- [x] 2.3 Replace the known-broken operator-surface icons and validate the rendered Homepage config
