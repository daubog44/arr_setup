## MODIFIED Requirements

### Requirement: Shared orchestration contract

The supported entrypoints MUST expose a Cobra-owned operator surface rather than a staged Python fallback.

#### Scenario: Wrapper entrypoints run the supported operator path

- **WHEN** an operator runs `.\haac.ps1 <args>` or `sh ./haac.sh <args>`
- **THEN** the wrapper MUST execute the repo-local Cobra binary for the supported operator surface
- **AND** it MUST NOT silently fall back to `scripts/haac.py`

#### Scenario: Steady-state wrapper execution avoids per-run recompilation

- **WHEN** the repo-local Cobra binary has already been built
- **THEN** wrapper execution MUST use that binary directly
- **AND** it MUST NOT keep using `go run` on every invocation as the steady-state path
