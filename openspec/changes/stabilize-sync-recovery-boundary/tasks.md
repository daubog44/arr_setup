## 1. Sync recovery

- [x] 1.1 Update the explicit sync path so it decides ref-state before checkpointing and safely preserves dirty tracked changes across a fast-forward
- [x] 1.2 Add focused regression coverage for the behind-plus-dirty sync path and any new Git helper behavior

## 2. Contract and validation

- [x] 2.1 Update the stable bootstrap-boundaries spec with the safer sync recovery rule
- [x] 2.2 Validate with OpenSpec and targeted tests, then use the fixed sync path to reconcile the current local/remote repo state
