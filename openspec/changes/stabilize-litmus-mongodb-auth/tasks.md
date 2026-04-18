## 1. Stable secret source

- [x] 1.1 Add a repo-managed Litmus MongoDB SealedSecret generated from `.env`
- [x] 1.2 Point the Litmus Application at the stable existing Secret and single-node Mongo topology

## 2. Migration and verification

- [x] 2.1 Add focused regression coverage for the generated secret staging path
- [x] 2.2 Reinitialize the existing Litmus MongoDB data once under the new topology and validate with OpenSpec, render gates, and a live Litmus post-install reconciliation
