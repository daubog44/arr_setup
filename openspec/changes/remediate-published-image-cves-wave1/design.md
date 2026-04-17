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
