## Why

Operator-facing surfaces are still rough in two places that the user hits immediately. Homepage renders broken image placeholders for some first-class services, and live cluster evidence shows the `semaphore-bootstrap` job succeeds while the schedules it reconciles come back unnamed and inactive, which makes post-install automation hard to see and trust from the UI.

The current Semaphore bootstrap logic also embeds its automation definitions directly inside a long Job script. That keeps the main operator contract clean, but it still leaves the post-install surface hard to extend and harder to review as the stack grows.

## What Changes

- Extract Semaphore post-install bootstrap logic and its maintenance automation definitions into dedicated repo-managed files consumed only by the post-install Job.
- Reconcile Semaphore schedules with the API fields it actually persists so schedules become named, active, and visible in the UI.
- Extend the Homepage route catalog so entries can reference repo-managed icon assets and optional widget metadata without introducing a second source of truth.
- Replace the known-broken Homepage service icons for first-class operator surfaces with supported repo-managed assets.

## Capabilities

### New Capabilities

- `postinstall-automation-catalog`: Defines repo-managed post-install automation inputs that are consumed by bootstrap automation instead of being embedded ad hoc in orchestration files.

### Modified Capabilities

- `public-ui-surface`: Homepage entries now need to support repo-managed custom icon assets and optional widget metadata from the official route catalog.
- `semaphore-bootstrap-readiness`: Semaphore bootstrap now needs to reconcile named, active schedules from the repo-managed post-install catalog.

## Impact

- Affected code: `k8s/charts/haac-stack/templates/_helpers.tpl`, `k8s/charts/haac-stack/charts/mgmt/templates/homepage.yaml`, `k8s/charts/haac-stack/charts/mgmt/templates/semaphore-bootstrap.yaml`, and the route catalog under `k8s/charts/haac-stack/`.
- Affected systems: Homepage rendering, Semaphore bootstrap automation, and operator-visible maintenance schedules.
