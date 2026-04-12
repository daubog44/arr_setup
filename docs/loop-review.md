# HaaC Loop Review

Review is part of the loop, not an optional epilogue.

## Validation Ladder

Bootstrap-affecting work should validate in this order when applicable:

1. `openspec validate <change>`
2. `python scripts/haac.py check-env`
3. `python scripts/haac.py doctor`
4. `python scripts/haac.py task-run -- -n up`
5. `python -m py_compile scripts/haac.py scripts/haac_loop.py scripts/hydrate-authelia.py`
6. `helm template haac-stack k8s/charts/haac-stack`
7. `kubectl kustomize k8s/bootstrap/root`
8. `kubectl kustomize k8s/platform`
9. `kubectl kustomize k8s/workloads`
10. `task up` or wrapper equivalent when the real environment is available
11. Playwright MCP browser navigation of the emitted public URLs when the round reaches endpoint verification

If a step is not applicable, say why. Do not collapse `check-env` into `doctor`; they validate different surfaces.

## Public URL Verification

If a round emits or verifies public URLs:

- run `verify-web` or equivalent HTTP-level verification first
- then use Playwright MCP to open the resulting URLs in a real browser context
- record which URLs were navigable, which redirected to auth, and which were broken

Accepted browser outcomes depend on the service:

- public services should load their real page shell
- protected services may land on the expected auth page or login redirect
- broken TLS, DNS, blank pages, or navigation failures are not acceptable

## Review Gates

Spawn or emulate targeted review before closeout when touching:

- `.env`, `.ssh`, secrets, Cloudflare, auth, or bootstrap trust boundaries
- `Taskfile.yml`, `scripts/haac.py`, `scripts/haac_loop.py`, `.tools`, or WSL bridging
- `ansible/`, `tofu/`, or `k8s/` cross-layer behavior

Required review perspectives:

- architecture and consistency
- security
- operator usability and rollback/recovery

## Failure Handling

- fail fast on secret exposure, destructive commands, or incorrect source-of-truth duplication
- retryable failures should be retried only when the retry condition is explicit
- if `check-env` fails, record it as the live-environment preflight blocker instead of summarizing the round as a generic `doctor` or `task up` failure
- if `task up` cannot run end to end, record the exact blocker and the furthest verified phase
