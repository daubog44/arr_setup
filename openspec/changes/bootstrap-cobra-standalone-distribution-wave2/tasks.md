## 1. OpenSpec Contracts

- [x] 1.1 Add the standalone CLI distribution capability spec and delta specs for the direct `haac up` / bootstrap boundary

## 2. Workspace Bootstrap

- [x] 2.1 Implement a workspace-aware `haac init` command that clones the repo and seeds `.env` from `.env.example`
- [x] 2.2 Add workspace resolution helpers so commands can target an explicit initialized workspace without assuming the current process already started inside the repo

## 3. Tooling Lifecycle

- [x] 3.1 Extend `install-tools` with explicit scope and workspace targeting
- [x] 3.2 Add `update-tools` and version metadata handling for managed binary refreshes

## 4. Distribution And Docs

- [x] 4.1 Add version metadata wiring plus versioned release artifact config for the Cobra binary
- [x] 4.2 Update README and operator reference docs so the direct `haac` binary is documented as the primary product surface

## 5. Validation

- [x] 5.1 Validate OpenSpec plus Go tests and command-level smoke tests for `init`, `install-tools`, `update-tools`, and `version`
- [x] 5.2 Re-run the supported bootstrap acceptance ladder needed for a bootstrap-surface change
