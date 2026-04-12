## 1. Session Worklog Selection

- [x] 1.1 Update loop worklog resolution to prefer the latest same-day worklog for the requested slug before creating a new minute-stamped file
- [x] 1.2 Keep reused worklog header synchronization intact after the new path-selection logic

## 2. Regression Coverage

- [x] 2.1 Add CLI-level regression coverage proving `run`, `prompt`, and `worklog` reuse the same same-day worklog path for a repeated slug
- [x] 2.2 Add a focused check that the runner still creates a new minute-stamped file when no matching same-day worklog exists

## 3. Validation And Closeout

- [x] 3.1 Validate the new change with `openspec validate reuse-loop-session-worklog`
- [x] 3.2 Record the duplicate-worklog evidence, chosen reuse rule, and fix boundary in the session worklog
