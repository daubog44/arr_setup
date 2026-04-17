## Why

The public operator surface is still not stable enough. On April 17, 2026, browser verification hit `https://headlamp.nucleoautogenerativo.it/` and received Cloudflare `502 Bad gateway` while the in-cluster pod still showed `Running` and `Ready=True`. Live cluster inspection showed the singleton Headlamp pod running on `haacarr-worker2`, and both the pod and node recorded recent `NodeNotReady` events. At the same time, the rendered EndpointSlice for `service/headlamp` showed `ready: false` even while the container itself was up.

The same round later reproduced the same outward symptom on `https://home.nucleoautogenerativo.it/`: Cloudflare `502`, an EndpointSlice with `ready: false`, and a probe configuration that still relied on the one-second default timeout for a Next.js healthcheck.

This breaks the operator contract because management UIs can disappear from the public surface even when GitOps itself looks healthy. The repo already treats Homepage, Authelia, and Ntfy as control-plane workloads; Headlamp was the inconsistent placement, and both Headlamp and Homepage still shared fragile one-second probe budgets.

## What Changes

- Treat Headlamp as a control-plane operator surface instead of leaving it on arbitrary workers.
- Make singleton operator-surface HTTP probes less brittle so short response spikes do not flap Headlamp or Homepage out of Endpoints.
- Tighten browser verification so gateway failures are reported as gateway failures, not as misleading auth fallback errors or generic content timeouts.

## Capabilities

### New Capabilities

- `headlamp-operator-surface`: Headlamp and sibling singleton operator surfaces remain reachable without fragile worker placement or one-second probe budgets.

### Modified Capabilities

- `task-up-bootstrap`: browser verification must distinguish real operator-route edge/gateway outages from successful authenticated UIs.

## Impact

- Affected code will primarily live in `k8s/charts/haac-stack/charts/mgmt/templates/headlamp.yaml`, `k8s/charts/haac-stack/charts/mgmt/templates/homepage.yaml`, and `scripts/verify-public-auth.mjs`.
- The change stays narrow: it does not alter public hostnames or auth strategy, only the stability contract of existing operator routes.
