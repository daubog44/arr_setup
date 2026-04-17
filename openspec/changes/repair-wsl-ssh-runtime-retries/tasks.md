## 1. Retry safety

- [x] 1.1 Recreate the Windows/WSL-backed SSH tunnel command on every retry attempt
- [x] 1.2 Isolate runtime-backed SSH materials per Windows-side session so parallel calls do not share the same WSL temp directory
- [x] 1.3 Add regression tests for the retry path and runtime isolation

## 2. Verification

- [x] 2.1 Validate with OpenSpec, targeted tests, and the official reconcile dry-run/live path
