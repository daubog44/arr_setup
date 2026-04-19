## Context

The repo-managed media stack already assumes a Jellyfin admin identity through `JELLYFIN_ADMIN_*` / `HAAC_MAIN_*`, but the actual Jellyfin deployment does not currently consume those values during first run. Because the config PVC persists across rollouts, the bootstrap path has to handle both states:

- first run: no users exist, startup wizard incomplete
- steady state: admin already exists and startup wizard is complete

The safe first move is to teach `media:post-install` to reconcile the first-run state before Seerr attempts login.

## Goals / Non-Goals

**Goals:**
- Detect whether Jellyfin is still in first-run startup mode.
- Create or update the initial Jellyfin admin when first-run state is detected.
- Complete the startup wizard idempotently so later post-install steps see a stable Jellyfin auth surface.

**Non-Goals:**
- This wave does not yet configure Jellyfin libraries, metadata policies, hardware transcoding, or plugins.
- This wave does not add additional media applications.
- This wave does not yet wire TRaSH/Recyclarr profiles.

## Decisions

### 1. Use Jellyfin's startup endpoints instead of filesystem mutation

The live service already exposes `/Startup/User`, `/Startup/Configuration`, and `/Startup/Complete`. Using those HTTP endpoints keeps the bootstrap within the supported API surface and avoids brittle direct edits inside the Jellyfin config PVC.

Rejected alternative:
- Write Jellyfin config files directly in the PVC. That would be harder to keep version-safe and less observable than the startup API.

### 2. Bootstrap only when Jellyfin still reports first-run state

If `StartupWizardCompleted=true`, the bootstrap should not overwrite the existing Jellyfin admin. The operator should then rely on the configured `JELLYFIN_ADMIN_*` values to match the real admin or fail explicitly.

Rejected alternative:
- Force-reset the admin every run. That would be unsafe on existing installations and break user-managed Jellyfin credentials.

## Risks / Trade-offs

- [Risk] The startup API shape may shift across Jellyfin releases. -> Mitigation: use the upstream-tested endpoints and keep unit coverage around the first-run detection and payload shape.
- [Risk] Completing startup without library configuration leaves Jellyfin minimally bootstrapped. -> Mitigation: that is acceptable for this wave because the immediate contract needed by Seerr is admin auth, not full library curation.
