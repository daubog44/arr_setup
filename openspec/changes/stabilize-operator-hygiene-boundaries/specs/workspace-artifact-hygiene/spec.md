## MODIFIED Requirements

### Requirement: Cleanup removes current non-contract local artifact directories

The workspace cleanup surface MUST remove only the known disposable local artifact roots that are outside tracked repo content.

#### Scenario: operator runs the cleanup task after browser verification and local tooling sessions

- **WHEN** the operator runs `task clean-artifacts`
- **THEN** the cleanup path MUST remove the dedicated disposable roots owned by repo-local tooling
- **AND** it MUST leave tracked repo content untouched
- **AND** it MUST NOT depend on generic broken-path root names as part of the long-term cleanup contract

### Requirement: Sanctioned scratch roots can be pruned safely

The cleanup path MUST be allowed to prune empty directories inside sanctioned scratch roots without removing real repo content.

#### Scenario: `.tmp/` contains stale empty session directories

- **WHEN** the operator runs `task clean-artifacts`
- **THEN** empty directories under the repo-owned `.tmp/` scratch root MAY be removed
- **AND** the `.tmp/` root itself MUST remain available for future runtime use
