## 1. OpenSpec Hygiene Contract

- [x] 1.1 Finalize the proposal, design, and spec delta for `enforce-openspec-change-hygiene`

## 2. Loop Runner Detection

- [x] 2.1 Update `scripts/haac_loop.py` and `docs/haac-loop-prompt.md` so loop sessions surface completed-change closeout debt and scaffold-only change debt
- [x] 2.2 Add regression coverage for prompt and check output when no active changes exist but OpenSpec hygiene debt remains

## 3. Cleanup And Validation

- [x] 3.1 Remove scaffold-only change directories and archive the current completed changes so accepted deltas sync into `openspec/specs/`
- [ ] 3.2 Validate with `openspec validate enforce-openspec-change-hygiene`, `openspec validate --specs`, and focused loop CLI checks, then update the worklog and KB
