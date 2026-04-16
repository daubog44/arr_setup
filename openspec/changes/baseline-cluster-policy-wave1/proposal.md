## Why

The current stack already has explicit auth routing, Sealed Secrets, Trivy, and a supported Falco deployment model for unprivileged LXC. What it still lacks is a policy-enforcement layer: Kyverno is absent, Pod Security Admission labels are not repo-managed, and Falco does not yet ship a homelab-focused post-install rule baseline.

## What Changes

- Add a repo-managed Kyverno baseline with a pragmatic first wave of cluster policies.
- Add the Kyverno web UI path through Policy Reporter so policy results are visible in-cluster.
- Add repo-managed Pod Security Admission namespace labels with explicit carve-outs where elevated privileges are required.
- Add a Falco homelab rule pack and a post-install security phase that keeps those rules managed.

## Capabilities

### New Capabilities
- `cluster-policy-baseline`: repo-managed Kyverno baseline, Policy Reporter UI, and namespace security labeling.
- `falco-homelab-rules`: curated homelab-focused Falco rules and post-install rule reconciliation.

### Modified Capabilities
- `public-ui-surface`: the official UI catalog will need to carry the policy reporting UI when it is intentionally published.
- `falco-lxc-readiness`: enabled Falco must include the repo-managed homelab rule baseline in addition to the supported host-side sensor path.

## Impact

- Affected code will live under `k8s/platform/`, `k8s/charts/haac-stack/`, `ansible/`, and post-install bootstrap wiring.
- This wave adds enforcement and reporting layers but does not change the operator entrypoint contract.
