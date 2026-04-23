## ADDED Requirements

### Requirement: Standalone CLI can initialize a HaaC workspace

The standalone `haac` binary MUST be able to create a usable workspace from a Git source without requiring the operator to clone the repository manually first.

#### Scenario: Git workspace bootstrap
- **WHEN** the operator runs `haac init` with a target directory and a Git repository source
- **THEN** the CLI MUST clone the requested repository into that directory
- **AND** it MUST support selecting the desired revision or branch when one is provided

#### Scenario: `.env` scaffold seeding
- **WHEN** the cloned workspace contains `.env.example`
- **AND** `.env` does not already exist
- **THEN** `haac init` MUST create `.env` from `.env.example`
- **AND** it MUST tell the operator that filling `.env` is the next required manual step before `haac up`

### Requirement: CLI manages tool lifecycle by scope

The standalone CLI MUST manage the operator toolchain for either a workspace-local install or a user-global install target.

#### Scenario: Local tool bootstrap
- **WHEN** the operator runs `haac install-tools --scope local` against an initialized workspace
- **THEN** the CLI MUST install the portable binaries into that workspace
- **AND** it MUST record enough version metadata to skip unnecessary reinstalls on later runs

#### Scenario: Global tool bootstrap
- **WHEN** the operator runs `haac install-tools --scope global`
- **THEN** the CLI MUST install the supported portable binaries into a user-global bin location
- **AND** it MUST avoid writing those global binaries into the repo workspace

#### Scenario: Tool update aligns the managed versions
- **WHEN** the operator runs `haac update-tools`
- **THEN** the CLI MUST reconcile the managed tools against the configured versions
- **AND** it MUST NOT require a force-reinstall of already-matching binaries just to satisfy the update contract

### Requirement: CLI distribution is versioned and releasable

The standalone `haac` binary MUST be distributable as a versioned artifact from the repository.

#### Scenario: Tagged release packaging
- **WHEN** the repository publishes a tagged release for `haac`
- **THEN** the release pipeline MUST produce versioned archives for the supported platforms
- **AND** it MUST publish checksums alongside those archives

#### Scenario: Version introspection
- **WHEN** the operator runs `haac version`
- **THEN** the command MUST report the CLI version
- **AND** it MUST include enough build metadata to distinguish release builds from local development builds
