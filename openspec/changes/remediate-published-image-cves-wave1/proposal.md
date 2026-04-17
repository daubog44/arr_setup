## Why

The April 17, 2026 security triage wave confirmed that the current Trivy backlog is not just policy noise. Live cluster evidence still shows a concentrated vulnerability burden on repo-managed published services:

- aggregate vulnerability counts remain at `critical=176`, `high=387`, `medium=629`
- the heaviest reports are `flaresolverr=684`, `prowlarr=85`, `jellyfin=80`, `radarr=70`, `homepage=69`, `ntfy=49`, `sonarr=45`, and `headlamp=35`

Those services are pinned in source-controlled manifests and values, so the repo now needs a dedicated remediation wave that evaluates the current tags, upgrades low-risk images where upstream fixes exist, and records explicit blockers where safe upgrades are not yet available.

## What Changes

- Add a repo-managed remediation contract for published-service image CVEs.
- Inventory the highest-CVE published workloads and split them into low-risk upgrades versus stateful or compatibility-sensitive upgrades.
- Upgrade the low-risk published-service images that have upstream fixes available without changing the operator contract.
- Record blockers and next-step guidance for any image that remains pinned because a safe remediation path is not yet proven.

## Capabilities

### Added Capabilities

- `published-image-vulnerability-remediation`

## Impact

- Affected source files will primarily live under `k8s/charts/haac-stack/config-templates/values.yaml.template`, `k8s/charts/haac-stack/values.yaml`, and the chart templates that consume those image tags.
- Verification must include Trivy evidence before and after the upgrades, plus browser checks for touched public services.
