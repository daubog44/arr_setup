## Why

The public Headlamp route is still not a stable operator surface. On April 17, 2026, browser verification hit `https://headlamp.nucleoautogenerativo.it/` and received Cloudflare `502 Bad gateway` while the in-cluster pod still showed `Running` and `Ready=True`. Live cluster inspection showed the singleton Headlamp pod running on `haacarr-worker2`, and both the pod and node recorded recent `NodeNotReady` events. At the same time, the rendered EndpointSlice for `service/headlamp` showed `ready: false` even while the container itself was up.

This breaks the operator contract because a management UI can disappear from the public surface even when GitOps itself looks healthy. The repo already treats other singleton operator surfaces such as Homepage, Authelia, and Ntfy as control-plane workloads; Headlamp is the inconsistent exception.

## What Changes

- Treat Headlamp as a control-plane operator surface instead of leaving it on arbitrary workers.
- Make Headlamp HTTP probes less brittle so short response spikes do not flap the service out of Endpoints.
- Tighten browser verification so Headlamp gateway failures are reported as gateway failures, not as a misleading internal-login error.

## Capabilities

### New Capabilities

- `headlamp-operator-surface`: Headlamp remains reachable through the public operator surface without depending on an unstable worker placement.

### Modified Capabilities

- `task-up-bootstrap`: browser verification must distinguish a real Headlamp edge/gateway outage from a successful authenticated operator UI.

## Impact

- Affected code will primarily live in `k8s/charts/haac-stack/charts/mgmt/templates/headlamp.yaml` and `scripts/verify-public-auth.mjs`.
- The change stays narrow: it does not alter the public hostname or auth strategy, only the stability contract of the existing route.
