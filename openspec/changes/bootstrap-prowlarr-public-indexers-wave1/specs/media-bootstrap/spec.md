## ADDED Requirements

### Requirement: Repo-Managed Prowlarr Baseline Indexers

The media post-install flow MUST bootstrap a minimal repo-managed set of public Prowlarr indexers required for movie and TV request resolution after a destructive cold cycle.

#### Scenario: Fresh cluster restores baseline public indexers

- **WHEN** the operator runs `task down` and then `task up`
- **THEN** Prowlarr exposes at least one movie-capable public indexer and one TV-capable public indexer without manual UI work
- **AND** the configured indexers are synchronized into the managed downstream ARR apps

### Requirement: Schema-Driven Prowlarr Payloads

Prowlarr indexer bootstrap payloads MUST be derived from the live schema surface rather than from hand-written raw JSON contracts.

#### Scenario: Schema changes remain bootstrap-compatible

- **WHEN** the bootstrap reconciles a Prowlarr indexer
- **THEN** it derives the payload from `/api/v1/indexer/schema`
- **AND** only overrides the minimal required fields for the selected baseline indexer
