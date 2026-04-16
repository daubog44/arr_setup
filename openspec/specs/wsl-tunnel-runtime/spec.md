# wsl-tunnel-runtime Specification

## Purpose
Define the retry contract for Windows/WSL-backed SSH tunnels used by the HaaC bootstrap and reconcile paths.

## Requirements
### Requirement: Windows/WSL tunnel retries recreate runtime-backed SSH materials

The repository MUST recreate any Windows/WSL runtime-backed SSH command inputs on every tunnel retry attempt.

#### Scenario: Windows tunnel attempt fails and retries

- **WHEN** the Windows bootstrap path retries an SSH tunnel or cluster session
- **THEN** each retry MUST rebuild the command that references the WSL runtime-backed private key and `known_hosts` files
- **AND** the retry loop MUST NOT reuse a command whose runtime-backed file paths were cleaned after the previous attempt
