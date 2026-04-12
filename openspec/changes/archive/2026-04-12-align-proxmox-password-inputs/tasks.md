## 1. Contract And Implementation

- [x] 1.1 Add the `task-up-bootstrap` delta that formalizes `LXC_PASSWORD` as the fallback source for `PROXMOX_HOST_PASSWORD`
- [x] 1.2 Keep the `scripts/haac.py` merged-environment fallback and ensure explicit host-password overrides still win

## 2. Regression Coverage And Docs

- [x] 2.1 Add focused Python regression tests for fallback and explicit-override behavior without touching the real `.env`
- [x] 2.2 Update operator docs so the supporting command layer matches the documented password source-of-truth rule

## 3. Validation And Closeout

- [x] 3.1 Validate with `openspec validate align-proxmox-password-inputs`, `python scripts/haac.py check-env`, `python scripts/haac.py doctor`, `python scripts/haac.py task-run -- -n up`, `python -m py_compile scripts/haac.py tests/test_haac.py`, `python -m unittest discover -s tests -p "test_haac.py" -v`, Helm render, and Kustomize renders
- [x] 3.2 Review the `scripts/haac.py` diff for architecture, security, and operator-usability impact; live `task up` is not required unless a local validation step exposes a new bootstrap failure
