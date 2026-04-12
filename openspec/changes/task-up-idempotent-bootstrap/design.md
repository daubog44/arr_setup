## Overview

This change makes `task up` an explicitly convergent bootstrap entrypoint. The run must be safe to execute on a clean environment, a partially bootstrapped environment, or an already aligned environment without requiring manual cleanup between attempts.

## Design Goals

- Keep the existing one-command operator model.
- Make reruns safe by deriving behavior from real state, not from optimistic first-run assumptions.
- Preserve clear phase boundaries and improve failure messages instead of hiding partial progress.
- Avoid duplicate side effects in GitOps publication, Cloudflare reconciliation, and public endpoint reporting.

## Non-Goals

- This change does not define full disaster recovery or backup restore flows.
- This change does not require destroying and recreating infrastructure to prove correctness.

## Current Gaps

- The stable bootstrap spec does not yet define rerun semantics.
- `task up` chains multiple mutating systems, but the contract does not clearly say which phases are convergent and which failures require operator intervention.
- The archive closeout now provides stable specs and archived change history, but the bootstrap path itself still lacks an explicit rerun-safe contract.

## Implementation Shape

1. Add stable requirements for rerun-safe `task up` behavior.
2. Audit the current bootstrap phases in `Taskfile.yml` and `scripts/haac.py` for repeated-run side effects:
   - Git sync and push behavior
   - OpenTofu init/apply reuse
   - Ansible rerun safety
   - GitOps bootstrap when ArgoCD and workloads already exist
   - Cloudflare reconciliation when records and tunnel rules already exist
   - verification and URL summary behavior on rerun
3. Tighten phase reporting so failures say which convergent checkpoint was last verified.
4. Validate the resulting contract with both dry-run and repeated-run checks, using a second `task up` as the main operator acceptance test when the environment is available.

## Validation Strategy

- `openspec validate task-up-idempotent-bootstrap`
- `python -m py_compile scripts/haac.py scripts/haac_loop.py`
- `task -n up`
- focused bootstrap helper checks that do not mutate unrelated state
- `task up` followed by a second `task up` in the real environment when reachable

## Risks

- Some phases may currently be convergent in practice but not yet report their state clearly enough.
- Rerun-safe behavior must not hide real drift or degraded state behind false "already done" shortcuts.
