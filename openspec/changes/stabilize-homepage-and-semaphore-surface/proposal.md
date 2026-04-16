## Why

The current operator-facing UI surface still has two avoidable quality gaps: Homepage renders broken or generic service cards even though widget metadata is already present in the repo, and Semaphore bootstrap creates schedules that exist in the API but remain inactive in the UI. These are visible operator regressions, so they should be fixed through repo-managed surface contracts instead of ad hoc cluster edits.

## What Changes

- Render Homepage widget and site-monitor metadata from the existing ingress catalog instead of dropping it at template time.
- Standardize broken Homepage icons on supported icon sources so official cards do not render missing images.
- Keep Homepage widget credentials repo-managed through the existing secret path rather than hardcoding them into the config map.
- Extract the long Semaphore post-install bootstrap shell into a file-backed script resource and fix schedule payloads so recurring jobs are created as active schedules with stable names.

## Capabilities

### New Capabilities
- `homepage-dashboard-surface`: Homepage cards, icons, site monitors, and secret-backed widgets render from the repo-managed catalog without broken assets.

### Modified Capabilities
- `semaphore-bootstrap-readiness`: Semaphore bootstrap must create active, operator-visible recurring schedules and keep the post-install script modular.

## Impact

- Affected code lives under `k8s/charts/haac-stack/`, `scripts/haac.py`, and OpenSpec specs.
- This wave improves the operator-facing UI surface and post-install modularity without changing the supported entrypoint contract.
