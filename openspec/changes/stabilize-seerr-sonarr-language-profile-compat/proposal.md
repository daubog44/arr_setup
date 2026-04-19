## Why

After fixing Seerr ARR option discovery, `media:post-install` now fails when persisting the Sonarr settings payload:

```text
POST /api/v1/settings/sonarr
HTTP 400
{"message":"request.body.activeLanguageProfileId should be number"}
```

Live evidence on April 18, 2026 showed Seerr `POST /api/v1/settings/sonarr/test` returns `languageProfiles=null` for the current Sonarr setup.

Official Seerr source confirms the intended contract:

- [`src/components/Settings/SonarrModal/index.tsx`](https://github.com/seerr-team/seerr/blob/main/src/components/Settings/SonarrModal/index.tsx) submits `activeLanguageProfileId: undefined` and `activeAnimeLanguageProfileId: undefined` when those values are absent
- [`seerr-api.yml`](https://github.com/seerr-team/seerr/blob/main/seerr-api.yml) describes `activeLanguageProfileId` as a numeric field, not a required nullable object

The bootstrap currently sends `null`, which does not match the supported payload shape.

## What Changes

- Align the Sonarr settings payload with the official Seerr client contract by omitting language-profile fields when Sonarr does not expose them.
- Add regression coverage for the no-language-profile case.

## Capabilities

### New Capabilities

- `seerr-sonarr-language-profile-compat`: Define the supported bootstrap payload shape for Sonarr v4 environments without language profiles.

### Modified Capabilities

- `arr-stack-surface`: Media post-install must remain compatible with Sonarr instances that do not expose language profiles.

## Impact

- Affected code lives in [scripts/haac.py](C:/Users/Utente/OneDrive%20-%20ITS%20Tech%20Talent%20Factory/Desktop/dev/arr_setup-main/scripts/haac.py) and [tests/test_haac.py](C:/Users/Utente/OneDrive%20-%20ITS%20Tech%20Talent%20Factory/Desktop/dev/arr_setup-main/tests/test_haac.py).
- Verification must include OpenSpec validation, targeted Python unit tests, and a live `media:post-install` rerun that progresses beyond Sonarr settings persistence.
