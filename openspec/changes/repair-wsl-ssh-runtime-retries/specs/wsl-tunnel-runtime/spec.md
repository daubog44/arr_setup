## ADDED Requirements

### Requirement: Windows/WSL tunnel retries recreate isolated runtime-backed SSH materials

The repository MUST recreate any Windows/WSL runtime-backed SSH command inputs on every tunnel retry attempt, and concurrent Windows-side sessions MUST NOT share the same WSL runtime directory by default.

#### Scenario: Windows tunnel attempt fails and retries

- **WHEN** the Windows bootstrap path retries an SSH tunnel or cluster session
- **THEN** each retry MUST rebuild the command that references the WSL runtime-backed private key and `known_hosts` files
- **AND** the retry loop MUST NOT reuse a command whose runtime-backed file paths were cleaned after the previous attempt

#### Scenario: Concurrent Windows-side sessions stage SSH materials

- **WHEN** two Windows-side tunnel or cluster-session calls run close together
- **THEN** each call MUST use its own scoped WSL runtime directory for staged private keys and `known_hosts`
- **AND** cleanup from one call MUST NOT remove runtime-backed SSH materials still in use by another call
