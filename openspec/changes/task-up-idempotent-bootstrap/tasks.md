## 1. Stable Contract

- [x] 1.1 Add the new `task-up-idempotence` capability spec covering rerun-safe bootstrap semantics
- [x] 1.2 Add a delta spec for `task-up-bootstrap` so the stable bootstrap contract stays aligned with idempotent startup behavior

## 2. Bootstrap Audit And Implementation

- [ ] 2.1 Audit `Taskfile.yml` and `scripts/haac.py` for repeated-run side effects across sync, OpenTofu, Ansible, GitOps, Cloudflare, and verification
- [ ] 2.2 Implement the missing idempotence guards or phase-aware recovery behavior found in that audit
- [ ] 2.3 Ensure the operator-facing output reports the last verified phase and whether a full rerun is safe

## 3. Validation And Documentation

- [ ] 3.1 Align `README.md`, `AGENTS.md`, and `docs/runbooks/task-up.md` with the final idempotence contract
- [ ] 3.2 Validate the change with `openspec validate task-up-idempotent-bootstrap`, `task -n up`, and focused bootstrap checks
- [ ] 3.3 When the real environment is available, run `task up` twice and record the second-run behavior as the acceptance proof
