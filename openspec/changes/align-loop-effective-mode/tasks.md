## 1. Session Mode Plumbing

- [ ] 1.1 Refactor loop session setup so `run`, `prompt`, and `worklog` all resolve the selected active changes and effective mode through shared helpers
- [ ] 1.2 Update worklog creation or reuse so the `mode` and `active_changes` header lines stay aligned with the effective session state

## 2. CLI Regression Coverage

- [ ] 2.1 Add a lightweight regression check for the apply-with-no-active-change path across `run --dry-run`, `prompt`, and `worklog`
- [ ] 2.2 Verify the helper behavior still stays correct for explicit discovery mode and normal apply mode with active changes

## 3. Validation And Closeout

- [ ] 3.1 Validate the new change with `openspec validate align-loop-effective-mode`
- [ ] 3.2 Record the exact evidence, impacted commands, and fix boundary in the session worklog
