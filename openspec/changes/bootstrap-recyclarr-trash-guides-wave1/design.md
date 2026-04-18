## Context

Recyclarr is already deployed as a CronJob, but it still relies on a placeholder config path. The missing inputs are not long-lived operator secrets from `.env`; they are the live ARR API keys generated inside each app.

Official Recyclarr guidance supports:

- one config file spanning Sonarr and Radarr
- `!secret` references for base URLs and API keys
- template-driven setup for Sonarr v4 and Radarr quality policy

The repo needs a bootstrap path that turns those pieces into a repeatable cluster-side configuration.

## Goals / Non-Goals

**Goals:**
- Ship the deterministic `recyclarr.yml` as repo-managed content.
- Generate only the runtime `secrets.yml` from the live ARR API keys.
- Run an immediate sync during `media:post-install`.
- Keep the scheduled CronJob as the steady-state reconciler after bootstrap.

**Non-Goals:**
- This wave does not add indexer credentials or tracker-specific policy.
- This wave does not attempt per-user profile customization beyond a sensible repo default.
- This wave does not migrate live ARR API keys into Git-tracked artifacts.

## Decisions

### 1. Split static config from runtime secrets

Manage Recyclarr as:

- repo-managed `recyclarr.yml` mounted from a ConfigMap
- runtime-generated `secrets.yml` mounted from a Secret created by `media:post-install`

Rejected alternatives:
- Manually edit a PVC. That keeps the repo blind to the quality policy and adds mutable drift.
- Commit live ARR API keys into Git-tracked files. That violates the repo’s secret boundary.

### 2. Start with a 1080p-focused profile set

The first wave will favor broadly compatible, storage-conscious defaults that fit the current Jellyfin Movies/TV topology:

- Sonarr v4: `sonarr-quality-definition-series`, `sonarr-v4-quality-profile-web-1080p`, `sonarr-v4-custom-formats-web-1080p`
- Radarr: explicit 1080p/HD-focused profile sync using official TRaSH/Recyclarr patterns

This is the safest first move for the current stack. Higher-bitrate UHD or specialized anime profiles can become follow-up waves once the default quality sync is stable.

### 3. Run bootstrap sync by creating a Job from the CronJob

After the runtime Secret exists, `media:post-install` should create a one-off Job from the `recyclarr` CronJob, wait for completion, and fail closed if the sync job errors. The CronJob then remains the weekly steady-state reconciler.

### 4. Verify by observing live profile convergence

The wave is only done when:

- Recyclarr sync completes successfully during `media:post-install`
- Radarr and Sonarr no longer rely solely on the untouched stock profile surface for the repo-managed default flow

## Risks / Trade-offs

- [Risk] Template names or guide defaults evolve upstream. -> Mitigation: base the config on official Recyclarr template identifiers and keep the template content centralized.
- [Risk] Runtime ARR API keys are not available during early failures. -> Mitigation: place the Recyclarr bootstrap after the existing ARR liveness and API-key discovery gates.
