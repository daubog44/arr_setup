# Design

## Scope

This change is structural. It does not change the desired cluster topology, auth model, or Cloudflare surface.

It touches:

- Task orchestration boundaries in `Taskfile.yml`
- Git state and publication logic in `scripts/haac.py`
- low-level Git helper placement in `scripts/haaclib/`

## Bootstrap Boundary

`task up` is the product path. It still needs GitOps publication, but it should not also own remote merge policy.

New boundary:

- `task sync`
  - explicit operator path for checkpoint + merge policy
- `task up`
  - bootstrap, reconcile, publish, verify
  - if the branch is behind or diverged, fail with guidance instead of auto-merging

## Publication Boundary

`push-changes` still needs to:

- regenerate GitOps outputs
- stage publishable files
- commit publishable diffs
- push to the configured GitOps revision

It no longer needs to:

- merge `origin/<revision>`
- auto-resolve branch divergence

That responsibility stays in the explicit `sync` path.

## Modularization Boundary

Low-level Git state inspection moves into `scripts/haaclib/gitstate.py`:

- repo presence
- remote existence
- dirty path discovery
- ref comparison

`scripts/haac.py` keeps orchestration and error policy only.

## Verification

- `openspec validate bootstrap-boundaries-and-modularization`
- `python -m py_compile scripts/haac.py scripts/haac_loop.py scripts/hydrate-authelia.py`
- `helm template haac-stack k8s/charts/haac-stack`
- `kubectl kustomize k8s/bootstrap/root`
- `kubectl kustomize k8s/platform`
- `kubectl kustomize k8s/workloads`
- `python scripts/haac.py task-run -- -n up`
