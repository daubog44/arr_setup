## Design

### Scope boundary

This wave is not a blanket image churn pass across the whole homelab. It focuses only on repo-managed services that are both:

- visible on the operator surface or otherwise published through the normal stack
- responsible for a meaningful share of current critical or high Trivy findings

### Upgrade strategy

The remediation order will follow blast radius:

1. low-risk management and utility services such as `homepage`, `ntfy`, and `headlamp`
2. media helper services such as `flaresolverr`, `prowlarr`, `radarr`, and `sonarr`
3. heavier or more compatibility-sensitive services such as `jellyfin`

Each candidate image must be checked against the upstream release source before any version bump. The repo must prefer source-template version updates over report suppression, ignore files, or dashboard filtering.

Wave1 will upgrade the low-risk services whose upstream releases are both newer and clearly source-aligned:

- `homepage` `v1.10.1` -> `v1.12.3`
- `ntfy` `v2.19.2` -> `v2.21.0`
- `headlamp` `v0.40.1` -> `v0.41.0`
- `authelia` `4.39.15` -> `4.39.19`
- `jellyfin` `10.11.6` -> `10.11.8`

`jellyfin` needs one additional rollout safeguard beyond the image bump: because it is GPU-bound and mounts a `ReadWriteOnce` config PVC, the deployment must use `Recreate` so the old pod releases the scheduling slot before the new version is admitted.

The highest remaining blockers after those upgrades are expected to be:

- `flaresolverr`, where the pinned image is already at the latest upstream release tag `v3.4.6`
- `prowlarr`, `radarr`, and `sonarr`, where the repo uses LinuxServer image tags that are not safely mappable one-to-one from the upstream application release stream without a separate compatibility pass

### Safety rules

- keep upgrades bounded to services whose tags are already source-controlled in the HaaC stack values
- do not weaken authentication, storage, or network policy as a side effect of a version bump
- if an image cannot be safely upgraded in this wave, document the blocker and leave the workload pinned rather than guessing

### Verification

- `openspec validate remediate-published-image-cves-wave1`
- `python scripts/haac.py check-env`
- `python scripts/haac.py doctor`
- `python -m py_compile scripts/haac.py scripts/haac_loop.py scripts/hydrate-authelia.py`
- `python -m unittest discover -s tests -p "test_haac.py" -v`
- `helm template haac-stack k8s/charts/haac-stack`
- `kubectl kustomize k8s/platform`
- `kubectl kustomize k8s/workloads`
- `python scripts/haac.py task-run -- -n up`
- live Trivy comparison for the touched workloads before and after deployment
- browser verification for the touched public services
