## ADDED Requirements

### Requirement: ARR end-to-end verification is an explicit operator action

The repo MUST expose one supported verifier for the media request-to-import path without making `task up` download content automatically.

#### Scenario: The operator runs the ARR verifier

- **WHEN** the operator runs the dedicated ARR flow verification task
- **THEN** the repo MUST verify a real request path through Seerr, ARR search, the downloader, the NAS-backed media root, and Jellyfin visibility
- **AND** the verifier MUST be rerunnable without requiring manual UI bootstrapping first

### Requirement: The ARR verifier uses safe viable candidates

The verifier MUST choose a safe title from a curated candidate set instead of relying on a single brittle hardcoded title.

#### Scenario: A candidate is selected

- **WHEN** the verifier chooses a movie for the live round
- **THEN** it MUST confirm that Seerr can resolve the title
- **AND** it MUST confirm that the configured Prowlarr movie indexer path returns seeded results for the matching title/year combination
- **AND** it MUST fail closed with a concrete blocker if no viable candidate exists

### Requirement: The verifier classifies the real blocker

The verifier MUST not collapse distinct media-path failures into a generic “ARR broken” outcome.

#### Scenario: The flow cannot reach imported media

- **WHEN** the live verifier fails before Jellyfin can see the title
- **THEN** the output MUST classify the furthest verified stage
- **AND** it MUST identify whether the blocker is search/indexer drift, downloader/VPN drift, NAS/import drift, or Jellyfin drift
