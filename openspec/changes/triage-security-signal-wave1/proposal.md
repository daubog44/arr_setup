## Why

The security surfaces added in the April 17, 2026 bootstrap waves now emit a large volume of Trivy, Kyverno, and Falco findings, but the current operator path does not distinguish urgent defects from expected homelab noise.

Live cluster evidence shows four concrete problems:

- Kyverno `require-pod-requests-limits` failures are real for active repo-managed workloads in `argocd`, `security`, and `chaos`, specifically the `argocd-redis` init container, `falco-falcosidekick`, `falco-falcosidekick-ui`, `falco-falcosidekick-ui-redis`, and `litmus-mongodb` volume-permissions path.
- Kyverno Policy Reporter is also still carrying zero-replica historical ReplicaSets from older Argo CD and Trivy rollouts, so the dashboard currently mixes active defects with migration residue from pre-fix revisions.
- Falco warnings are being flooded by the custom `HAAC Socket Tool Execution` rule on loopback-only health tooling such as `nc -zv localhost 8501/8502/8503`, which drowns out higher-signal host activity.
- Trivy dashboards still show a meaningful CVE backlog on repo-managed published workloads, with the current concentration dominated by `flaresolverr`, `prowlarr`, `jellyfin`, `radarr`, `homepage`, and `ntfy`.

This is operator-visible because the dashboards are now part of the normal management surface, and the user needs a repo-managed answer for which findings are severe, which ones are tradeoffs, and which ones should be fixed immediately.

## What Changes

- Add a repo-managed triage contract for security dashboards so the bootstrap path can classify urgent versus expected findings.
- Eliminate the real Kyverno resource-policy failures in repo-managed `argocd`, `security`, and `chaos` workloads.
- Clean up one-time rollout-history residue where that stale state would otherwise keep Policy Reporter red after the active workloads are fixed.
- Narrow the Falco host rule bundle so loopback-only socket probes stop flooding the Falco UI.
- Make Trivy dashboards more actionable by recording only failed policy-style checks while preserving vulnerability scanning.
- Open a dedicated follow-up change for the highest-CVE published images instead of hiding those results or disabling the scanner.

## Capabilities

### Added Capabilities

- `security-signal-triage`

### Modified Capabilities

- `cluster-policy-baseline`
- `falco-homelab-rules`

## Impact

- Affected code lives in `scripts/haac.py`, `scripts/verify-public-auth.mjs`, `tests/test_haac.py`, `Taskfile.yml`, `Taskfile.internal.yml`, and `Taskfile.security.yml`.
- Affected manifests live in `k8s/platform/applications/*.yaml`, `k8s/platform/argocd/install-overlay/*.yaml`, and `ansible/files/falco-rules/haac-homelab-rules.yaml`.
- Live verification must include the usual bootstrap ladder plus browser checks for Grafana, Kyverno Policy Reporter, and Falco.
