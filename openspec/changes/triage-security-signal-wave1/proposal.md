## Why

The security surfaces added in the April 17, 2026 bootstrap waves now emit a large volume of Trivy, Kyverno, and Falco findings, but the current operator path does not distinguish urgent defects from expected homelab noise.

Live cluster evidence shows three concrete problems:

- Kyverno `require-pod-requests-limits` failures are real and concentrated in `argocd`, `security`, and `chaos`, including `argocd-server`, `argocd-repo-server`, `argocd-redis`, `trivy-operator`, `falco-falcosidekick`, `falco-falcosidekick-ui`, `falco-falcosidekick-ui-redis`, `litmus-mongodb`, and `litmus-mongodb-arbiter`.
- Falco warnings are being flooded by the custom `HAAC Socket Tool Execution` rule on loopback-only health tooling such as `nc -zv localhost 8501/8502/8503`, which drowns out higher-signal host activity.
- Trivy dashboards are mixing real image CVEs with successful RBAC/config assessment records, so the top-line Grafana counts do not currently tell the operator which findings are actionable first.

This is operator-visible because the dashboards are now part of the normal management surface, and the user needs a repo-managed answer for which findings are severe, which ones are tradeoffs, and which ones should be fixed immediately.

## What Changes

- Add a repo-managed triage contract for security dashboards so the bootstrap path can classify urgent versus expected findings.
- Eliminate the real Kyverno resource-policy failures in repo-managed `argocd`, `security`, and `chaos` workloads.
- Narrow the Falco host rule bundle so loopback-only socket probes stop flooding the Falco UI.
- Make Trivy dashboards more actionable by recording only failed policy-style checks while preserving vulnerability scanning.

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
