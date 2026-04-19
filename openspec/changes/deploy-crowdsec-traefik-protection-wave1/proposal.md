## Why

The stack already ships Falco, Kyverno, and Trivy, but it still lacks a repo-managed ingress remediation layer that reacts to abusive client behavior and application-layer attacks. The operator explicitly wants CrowdSec installed and tuned for the current Traefik plus Cloudflare topology.

## What Changes

- Add a repo-managed CrowdSec installation in-cluster with the supported Kubernetes Helm surface.
- Integrate CrowdSec with Traefik through the supported bouncer and AppSec path, using access-log acquisition and ingress-level remediation.
- Add metrics and a Grafana surface if the supported chart exports them.
- Document the real security boundary: CrowdSec can improve L7 abuse remediation and virtual patching, while volumetric DDoS remains an edge-network concern already handled primarily by Cloudflare.

## Capabilities

### New Capabilities
- `crowdsec-ingress-protection`: Repo-managed CrowdSec installation, Traefik remediation, and observability for behavior-based ingress protection.

### Modified Capabilities
- `cluster-policy-baseline`: The security baseline must now include ingress remediation and document the CrowdSec plus Cloudflare split of responsibilities.

## Impact

- Affected code lives in `k8s/platform/`, `k8s/charts/haac-stack/`, `.env.example`, `scripts/haac.py`, `tests/test_haac.py`, and the security docs.
- Validation must include OpenSpec, render gates, live cluster reconcile, and at least one blocked AppSec-style probe against the Traefik edge.
