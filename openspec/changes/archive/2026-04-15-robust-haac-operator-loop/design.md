# Design

## Bootstrap and source-of-truth

The bootstrap path stays hybrid by design:

- `.env` is the operator source of truth
- OpenTofu and Ansible own infra plus host bootstrap
- ArgoCD owns cluster-side steady state

The robustness work should reduce ambiguity, not replace this model.

## Public UI and auth contract

All official browser-facing apps should continue to use one route catalog and one shared edge-auth contract through Authelia, with app-native auth disabled or bypassed where safe.

Homepage entries, aliases, and endpoint verification should remain derived from that same catalog.

## Orchestration modularization

`scripts/haac.py` should keep shrinking into thin orchestration while reusable logic moves into `scripts/haaclib/`.

This is a robustness goal because a monolithic runner makes bootstrap drift and regression review harder.

## Loop governance

The Ralph loop should keep doing three things:

- implement the highest-priority active change
- open one evidence-backed new change when a real gap appears
- stop when implementation, discovery, and review no longer expose actionable work inside the requested scope

This umbrella change provides the stable place to track that residual hardening work.
