## Design

### Evidence

- Browser verification on April 17, 2026 reached `headlamp.nucleoautogenerativo.it` and received `502 Bad gateway` from Cloudflare.
- Live cluster inspection showed:
  - `pod/headlamp-f964c8bc5-gjz8m` running on `haacarr-worker2`
  - recent `NodeNotReady` events on both the pod and `node/haacarr-worker2`
  - `discovery.k8s.io/v1 EndpointSlice/headlamp-*` rendered with `ready: false` and `serving: false`
- The Headlamp manifest currently has no `nodeSelector` or control-plane toleration, unlike other singleton operator services in `k8s/charts/haac-stack/charts/mgmt/templates/`.
- The manifest also leaves the HTTP probes on Kubernetes defaults for `timeoutSeconds`, which means a one-second timeout on `/`.
- Headlamp logs show repeated successful requests that can take roughly 1.5s to complete, so a one-second probe budget is unnecessarily fragile.

### Solution shape

This wave keeps the fix narrow and biased toward operator-surface stability:

- place the singleton Headlamp deployment on the control-plane node, matching Homepage, Authelia, and Ntfy
- add the control-plane toleration needed for that placement
- raise the HTTP probe timeout budget for `/` so transient latency does not flap the service out of the EndpointSlice
- update browser verification to fail fast on `502`, `Bad gateway`, or similar route-level errors with an accurate message

This is the right first move because it addresses the observed public outage directly without trying to solve every cause of transient worker instability in the same round.

### Verification

- `openspec validate stabilize-headlamp-operator-surface`
- `helm template haac-stack k8s/charts/haac-stack`
- `python scripts/haac.py task-run -- -n up`
- `task reconcile:argocd`
- `node scripts/verify-public-auth.mjs`
- explicit Playwright CLI navigation for Headlamp after reconcile
