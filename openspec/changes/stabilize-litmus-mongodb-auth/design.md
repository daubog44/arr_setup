## Design

The failure comes from chart behavior, not from the bootstrap script alone. Rendering the Litmus chart twice with the current values produces different `mongodb-replica-set-key` data for the `litmus-mongodb` Secret, while the root password stays fixed at `1234`. That makes the MongoDB replica-set key non-idempotent under GitOps.

The fix is to pin the MongoDB secret from `.env` and remove the unnecessary arbiter:

- generate a repo-managed SealedSecret named `litmus-mongodb-credentials`
- include `mongodb-root-password` and `mongodb-replica-set-key`
- configure `mongodb.auth.existingSecret` in the Litmus Application values so the subchart consumes that secret instead of generating a new one
- keep `architecture: replicaset` with `replicaCount: 1` but disable `mongodb.arbiter.enabled`, so Litmus uses a single-node replica set that matches the homelab shape and avoids extra DNS/member-auth failure modes

This keeps the source of truth in `.env`, aligns with the existing Sealed Secret workflow, and avoids secret drift. Because the current live MongoDB data was initialized with an arbiter-backed topology, the migration path includes a one-time reset of the Litmus MongoDB PVC so the single-node replica set can reinitialize cleanly; the Litmus admin and experiment catalog are then reseeded by the existing post-install automation.
