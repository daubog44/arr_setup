## 1. Contracts

- [x] 1.1 Add OpenSpec deltas for Italian-first media preference and explicit ARR naming templates
- [x] 1.2 Document the Seerr boundary so request brokering versus indexer and language enforcement is explicit

## 2. Implementation

- [x] 2.1 Extend the media bootstrap to reconcile exact Radarr, Sonarr, and Lidarr naming templates instead of rename booleans only
- [x] 2.2 Add repo-managed Italian-first preference logic for Radarr and Sonarr using supported custom-format and profile primitives
- [x] 2.3 Keep Bazarr and the docs aligned with the same Italian-first contract
- [x] 2.4 Add focused unit coverage for naming payloads and Italian preference reconciliation

## 3. Validation

- [x] 3.1 Validate with OpenSpec, Python tests, and a live `media:post-install` rerun
- [x] 3.2 Rerun the ARR verifier and confirm NAS import plus Jellyfin visibility still succeed with the new naming and language policy
