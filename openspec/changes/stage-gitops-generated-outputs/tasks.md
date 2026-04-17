## 1. Shared staging contract

- [x] 1.1 Centralize the repo-managed generated GitOps output paths in `scripts/haac.py`
- [x] 1.2 Reuse the shared staging list from `push-changes` and the pre-commit hook

## 2. Verification

- [x] 2.1 Add focused regression coverage for the generated-output staging list
- [x] 2.2 Validate with OpenSpec, unit tests, and a live bootstrap rerun that republishes the corrected platform secrets
