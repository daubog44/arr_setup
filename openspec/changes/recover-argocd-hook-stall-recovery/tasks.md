## 1. Recovery logic

- [x] 1.1 Detect same-revision ArgoCD operations that are stuck waiting on missing hook resources
- [x] 1.2 Add a safe repo-managed child-Application recycle path for that hook-stall case

## 2. Validation

- [x] 2.1 Add focused unit coverage for same-revision hook-stall detection and guarded recovery
- [x] 2.2 Validate with OpenSpec plus a live ArgoCD readiness rerun when the cluster is available
