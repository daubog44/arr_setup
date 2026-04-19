## Why

Live recovery on April 19, 2026 showed that GitOps readiness can still fail even after the K3s worker identity drift is repaired because the Kyverno admission webhook is deployed as a single replica.

- `haac-stack` and `kube-prometheus-stack` remained `OutOfSync` after ArgoCD recovered
- manual sync attempts failed with `failed calling webhook "validate.kyverno.svc-fail"` and `no endpoints available for service "kyverno-svc"`
- the only `kyverno-admission-controller` pod had frequent readiness gaps and restarts on a worker node, leaving the admission `Service` without endpoints during sync windows

This means `task up` still depends on a single Kyverno admission pod staying healthy while ArgoCD reconciles platform and workloads.

## What Changes

- Make the Kyverno admission controller highly available instead of single replica.
- Add placement hints so multiple admission replicas spread across nodes instead of concentrating on one worker.
- Validate the repo-managed Kyverno surface by rerunning ArgoCD readiness after the change is live.

## Capabilities

### New Capabilities
- `kyverno-admission-availability`: Keep the Kyverno admission webhook service available during ordinary pod restarts and node churn.

### Modified Capabilities
- `task-up-idempotence`: GitOps readiness must not depend on a single Kyverno admission replica remaining continuously available.

## Impact

- Affected code will primarily live in `k8s/platform/applications/kyverno-app.yaml.template`, the rendered GitOps output, and focused docs/spec artifacts.
- Live validation must include OpenSpec validation plus a rerun of ArgoCD readiness once the updated Kyverno topology is reconciled.
