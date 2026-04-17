## Why

Several Argo CD applications stay `Healthy` but `OutOfSync` even when the live cluster matches the repo-managed intent after server-side defaulting and mutation. On April 17, 2026 the affected apps were `kyverno`, `kube-prometheus-stack`, and `litmus`. Focused verification showed `kubectl diff` returned exit code `0` for the rendered `deletingpolicies.policies.kyverno.io` CRD, `kube-prometheus-stack-apiserver` `ServiceMonitor`, and `litmus-mongodb` `StatefulSet`, while Argo still reported drift.

This matters because `task up` currently leaves the operator with a noisy GitOps surface and no clear signal about whether drift is real or only a compare-strategy artifact.

## What Changes

- Enable Argo CD server-side diff on the affected applications that already rely on server-side apply and Kubernetes defaulting/mutation.
- Tighten the repo-managed application manifests so obvious implicit defaults that affect compare output are explicit where practical.
- Record the compare-strategy contract as a stable GitOps capability.

## Capabilities

### New Capabilities

- `argocd-server-side-diff`: GitOps applications that depend on server-side apply and Kubernetes defaulting/mutation use Argo CD server-side diff so false `OutOfSync` states do not persist.

## Impact

- Affected files live under `k8s/platform/applications/` plus a new stable OpenSpec capability.
- This change improves GitOps correctness without changing the public hostname contract or bootstrap entrypoints.
