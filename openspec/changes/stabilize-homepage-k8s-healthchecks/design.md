## Summary

This wave keeps the current Homepage deployment shape but fixes the parts that conflict with Homepage's documented Kubernetes runtime contract.

## Design

Homepage validates incoming hosts before serving requests. In Kubernetes, kubelet HTTP probes originate against the pod IP rather than the public ingress hostname, so the allow-list must include `$(MY_POD_IP):3000`. The official installation guide also exposes `/api/healthcheck` as the probe endpoint instead of `/`, which avoids coupling readiness to the UI route and host-validated page rendering.

The chart will therefore:

1. inject `MY_POD_IP` from the pod status field;
2. set `HOMEPAGE_ALLOWED_HOSTS` to include both the pod IP and the public hostname;
3. point both readiness and liveness probes at `/api/healthcheck`.

## Verification

- `helm template haac-stack k8s/charts/haac-stack`
- `python scripts/haac.py task-run -- reconcile:argocd`
- `node scripts/verify-public-auth.mjs`
- Playwright CLI navigation of `https://home.<domain>`

## Risks

- Adding pod-IP host allowance slightly widens the accepted host surface, but only to the current pod IP and only to satisfy internal kubelet probes.
- Homepage probe semantics depend on the upstream health endpoint staying stable; this is acceptable because it follows the project's documented Kubernetes contract.
