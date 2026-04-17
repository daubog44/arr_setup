## ADDED Requirements

### Requirement: Windows task streaming must not depend on the local code page

The repo-managed Windows bootstrap wrapper MUST decode streamed `task` output with a deterministic UTF-8 contract instead of the active workstation code page.

#### Scenario: WSL or remote tooling emits non-CP1252 bytes

- **WHEN** `python scripts/haac.py task-run -- up` streams output that contains bytes outside the active Windows code page
- **THEN** the wrapper MUST keep printing readable output instead of raising a local decode exception
- **AND** the bootstrap phase tracking logic MUST still receive the streamed lines
