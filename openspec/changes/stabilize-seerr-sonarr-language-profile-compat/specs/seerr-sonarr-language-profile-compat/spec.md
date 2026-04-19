## ADDED Requirements

### Requirement: Sonarr bootstrap omits absent language-profile fields

The media post-install bootstrap MUST match the official Seerr client payload shape when Sonarr exposes no language profiles.

#### Scenario: Missing Sonarr language profiles do not serialize as null

- **WHEN** Seerr Sonarr test output contains no `languageProfiles`
- **THEN** the bootstrap MUST omit `activeLanguageProfileId`
- **AND** the bootstrap MUST omit `activeAnimeLanguageProfileId`
- **AND** Sonarr settings persistence MUST NOT fail only because the absent language-profile fields were serialized as `null`
