## Context

The repo already has one public route catalog in `k8s/charts/haac-stack/values.yaml`, and both Homepage plus endpoint verification derive from it. That part is directionally correct, but the catalog currently only carries simple string metadata, so unsupported icon names render as broken images instead of a supported Homepage visual source.

Live cluster evidence also shows the issue with Semaphore is not that the bootstrap job never runs. The job is `Succeeded`, and its logs confirm that project, template, and schedule reconciliation execute. The actual drift is lower-level:

- the schedule payloads are written inline in the bootstrap shell script
- the payloads use `enabled` while the API persists `active`
- reconciled schedules come back with blank `name` values and `active: false`

That means the operator surface is stale even though the bootstrap job reports success.

## Goals / Non-Goals

**Goals:**
- Make Homepage render supported icons for all first-class operator surfaces.
- Keep Homepage metadata in the existing official route catalog instead of creating a second service list.
- Move Semaphore post-install bootstrap logic and schedule definitions into dedicated repo-managed files.
- Make Semaphore schedules converge as named and active resources.

**Non-Goals:**
- Rework the primary operator `task up` contract.
- Move infrastructure maintenance out of Semaphore.
- Introduce a second public-route or homepage catalog.

## Decisions

### Extract Semaphore bootstrap logic into mounted repo files

The YAML template should stop inlining the long bootstrap shell logic. Instead, the chart will mount:

- a bootstrap shell script
- a shell-friendly maintenance catalog file

The Job stays the execution surface, but the logic and data become reviewable, diffable repo assets.

Alternative considered:
- Keep the entire script inline and only patch the schedule payload. Rejected because it leaves the post-install surface brittle and directly contradicts the request to keep orchestration files from growing into giant blobs.

### Keep the automation catalog shell-friendly

The bootstrap container already relies on basic shell tooling. The smallest reliable path is a shell-friendly catalog format that can be sourced directly without adding `jq`, `yq`, or Python to the post-install container.

Alternative considered:
- A YAML or JSON catalog parsed at runtime. Rejected for this wave because it adds parser dependencies to a post-install job that currently does not need them.

### Use explicit `name` and `active` fields for Semaphore schedules

The bootstrap job should reconcile schedules with the fields the Semaphore API actually returns and stores. Each managed schedule gets:

- a stable non-empty display name
- `active: true`

Alternative considered:
- Keep sending `enabled: true`. Rejected because live API evidence already shows the persisted objects still come back inactive.

### Add supported Homepage icon metadata and optional widget passthrough

The route catalog already owns service identity, so the chart should allow Homepage entries to use valid supported icon identifiers and optional widget metadata from the same catalog into `services.yaml`.

Alternative considered:
- Mount repo-managed local icon assets in this wave. Rejected because supported built-in icon identifiers solve the currently broken operator surfaces with less chart plumbing, while still keeping all visual metadata centralized in the route catalog.

## Risks / Trade-offs

- `[Shell-friendly catalog format is less expressive than YAML]` -> Accept for this wave because the catalog only needs deterministic project/template/schedule records and benefits from zero extra runtime dependencies.
- `[Changing schedule payload fields may surface existing stale schedules]` -> Reconcile in place with stable IDs and names so later syncs converge rather than duplicate.
- `[Homepage widget passthrough could tempt secret sprawl in config maps]` -> Only add metadata passthrough in this wave; secret-backed widgets stay opt-in and must be sourced from explicit future changes.
- `[Built-in icon identifiers do not perfectly match every service logo]` -> Accept for this wave because the immediate defect is broken imagery, and supported icon sources restore a clean operator surface without adding more asset lifecycle.

## Migration Plan

1. Add delta specs for the post-install catalog, public UI surface, and Semaphore bootstrap readiness.
2. Move Semaphore bootstrap logic and maintenance definitions into dedicated chart files mounted into the Job.
3. Patch the bootstrap reconciliation to set schedule names plus `active: true`.
4. Replace broken Homepage icon metadata with supported icon identifiers and extend helpers to render optional widget metadata.
5. Re-render the chart locally and validate the live Semaphore API contract against the existing cluster evidence.

## Open Questions

- None for this wave. The required behavior is already constrained by live cluster evidence and the existing public route contract.
