## Context

Seerr on Sonarr v4 can legitimately return no language-profile options. The bootstrap already models that case internally, but it serializes the absent value as JSON `null`, while the official Seerr client omits the field entirely.

This is a pure payload-shape incompatibility. The smallest safe fix is to make the bootstrap payload match the official UI.

## Goals / Non-Goals

**Goals:**
- Keep Sonarr bootstrap compatible with Sonarr installs that expose no language profiles.
- Match Seerr’s official client submission behavior.

**Non-Goals:**
- This wave does not introduce custom language-profile policy.
- This wave does not change Radarr payload handling.

## Decisions

### 1. Omit absent language-profile fields

If no Sonarr language profile is available, do not send `activeLanguageProfileId` or `activeAnimeLanguageProfileId` at all. Preserve the rest of the payload unchanged.

Rejected alternative:
- Send `0` as a sentinel number. That would invent a value the official Seerr client does not send and risks selecting an invalid profile.

## Risks / Trade-offs

- [Risk] A future Seerr release could start requiring an explicit number for all Sonarr payloads. -> Mitigation: the fix mirrors the current upstream UI and OpenAPI contract, which is the best authoritative source available.
