## Design

### Scope boundary

This wave changes media preference and file naming only. It does not add a new request UI, it does not redesign the downloader path, and it does not expand Seerr beyond its upstream Radarr and Sonarr contract.

### Italian-first preference

The supported enforcement point is Radarr and Sonarr, not Seerr. Seerr can request media and choose the configured downstream servers, but it does not manage indexers directly and it does not replace ARR quality and language policy.

The repo should therefore:

1. keep Seerr pointed at the repo-managed Radarr and Sonarr services
2. add Italian-first language custom formats through the repo-managed policy surface
3. ensure the active quality profiles select those language rules deterministically
4. keep Bazarr as the subtitle fallback layer with `it,en`

The Italian preference should fail closed toward the intended language policy where the supported custom-format primitives make that possible, while still allowing operators to change it later through source control.

### Naming contract

The current bootstrap only enables rename toggles. The repo needs exact naming templates so imports, upgrades, and rescans stay deterministic.

The target pattern is:

- Radarr:
  - movie folder: `{Movie CleanTitle} ({Release Year})`
  - movie file: `{Movie CleanTitle} {(Release Year)} {imdb-{ImdbId}} {edition-{Edition Tags}} {[Custom Formats]}{[Quality Full]}{[MediaInfo 3D]}{[MediaInfo VideoDynamicRangeType]}{[Mediainfo AudioCodec}{ Mediainfo AudioChannels]}{[Mediainfo VideoCodec]}{-Release Group}`
- Sonarr:
  - series folder: `{Series TitleYear} [tvdbid-{TvdbId}]`
  - season folder: `Season {season:00}`
  - episode file: `{Series TitleYear} - S{season:00}E{episode:00} - {Episode CleanTitle:90} {[Custom Formats]}{[Quality Full]}{[Mediainfo AudioCodec}{ Mediainfo AudioChannels]}{MediaInfo AudioLanguages}{[MediaInfo VideoDynamicRangeType]}{[Mediainfo VideoCodec]}{-Release Group}`
- Lidarr:
  - artist folder: `{Artist Name}`
  - track file: `{Album Title}/{track:00} - {Track Title}`

These formats are narrow on purpose:

- they remain compatible with Jellyfin scanning
- they avoid folder names that embed volatile quality metadata
- they keep upgrade-safe release details in files where useful

### Verification

- `openspec validate prefer-italian-arr-naming-wave6`
- targeted Python tests for naming and Italian preference payloads
- `python scripts/haac.py task-run -- media:post-install`
- `python scripts/haac.py task-run -- verify:arr-flow`
- browser/API verification that Seerr stays on the login/request surface and Jellyfin still sees imported media

### Recovery and rollback

- `task media:post-install` remains the supported rerun path for naming and language drift
- rollback removes the explicit naming and language preference payloads without changing the downloader topology
