## Why

The Litmus chart currently lets the MongoDB subchart generate the replica-set secret at render time. Re-rendering the chart produces a different `mongodb-replica-set-key`, which means a partial pod restart can leave the MongoDB primary and arbiter on different internal credentials. The observable result is `ReplicaSetNoPrimary`, `AuthenticationFailed` on `__system`, and a broken `chaos:post-install` bootstrap path.

## What Changes

- move Litmus MongoDB credentials to a repo-managed SealedSecret generated from `.env`
- point the Litmus chart at that stable `existingSecret`
- simplify Litmus to a single-node replica set without the extra arbiter, which is unnecessary and brittle for this homelab topology
- validate the rendered output and live Litmus recovery path against the pinned secret

## Impact

- Litmus MongoDB credentials stop drifting between renders
- the Mongo topology matches the homelab reality instead of depending on an extra arbiter pod
- the ChaosCenter backend survives normal Argo syncs and pod restarts
- `task up` can complete the Litmus post-install phase without manual MongoDB restarts
