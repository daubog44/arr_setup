## Context

The repo already has one ingress catalog in `values.yaml.template`, but the published surface is still not treated as a full product contract. Falco is opt-in at the platform layer, Litmus is installed outside the main chart, Homepage groups are effectively hardcoded to Media and Management, and endpoint verification still infers auth as a boolean rather than a precise operator-facing posture. In parallel, several older bootstrap changes are still marked in-progress even though the live system and stable specs have moved past them.

## Goals / Non-Goals

**Goals:**
- Use one official UI catalog for published routes, Homepage links, and endpoint verification.
- Publish Falco and Litmus only when they are real, reachable product URLs.
- Make Authelia forward-auth the consistent default for official app UIs.
- Clean up the bootstrap OpenSpec backlog so `openspec list` reflects the real work state.
- Reconcile the live GitOps state and verify the resulting public URLs.

**Non-Goals:**
- Replace forward-auth with per-app native OIDC everywhere.
- Re-architect Falco itself or Litmus itself beyond what is needed for safe UI publication.
- Collapse every bootstrap spec into one document; the goal is cleanup and consistency, not deleting useful history.

## Decisions

- Use the existing `ingresses` catalog as the single public surface source of truth, but extend each route with `enabled`, `auth_enabled`, and Homepage metadata that can be consumed uniformly by templates and verification code.
- Keep Falco opt-in at the platform layer, and make its UI publication conditional on the same enablement flag so the catalog never advertises dead links.
- Publish Litmus through the same HTTPRoute and Homepage path as the rest of the stack instead of relying on ad hoc comments or out-of-band ingress assumptions.
- Protect official app UIs with Authelia forward-auth by default. This matches the current Traefik/Gateway architecture and avoids a fragile per-app OIDC migration.
- Archive stale active changes only after the accepted requirements are represented in stable specs or clearly superseded by them.

## Risks / Trade-offs

- [Protecting every UI route may surprise existing direct consumers] → Keep the auth posture explicit in the route catalog and final endpoint summary.
- [Falco route publication could create a dead link if Falco is disabled] → Make route generation, Homepage generation, and endpoint verification honor the same `enabled` flag.
- [Archiving active changes too aggressively could lose useful pending context] → Sync accepted requirements into stable specs first and archive only changes whose observable outcomes are already satisfied or superseded.
