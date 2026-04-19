## Context

The Seerr auth route behaves differently depending on whether Jellyfin is already configured:

- first run: it requires `hostname`, `port`, `useSsl`, and `serverType`
- rerun with Jellyfin already configured: those fields must be omitted or Seerr rejects the payload

The bootstrap already reads `public_settings` before Seerr auth, so the smallest fix is to derive the payload mode from that state instead of hardcoding the first-run branch forever.

## Goals / Non-Goals

**Goals:**
- Make the Seerr auth helper rerunnable.
- Preserve the working first-run payload for unconfigured Seerr installs.
- Keep the decision logic local to one helper.

**Non-Goals:**
- This wave does not change the later Seerr settings payloads.
- This wave does not add new media services or TRaSH logic.

## Decisions

### 1. Decide from Seerr public settings

If `public_settings.mediaServerType` already reports Jellyfin, the rerun auth payload should omit the connection fields and only send the user credentials. If no media server is configured yet, the helper should continue to send the first-run fields.

Rejected alternative:
- Catch the hostname-configured error and retry implicitly. That would hide the actual contract and keep the first request knowingly wrong.

## Risks / Trade-offs

- [Risk] Public settings may change shape in a future Seerr release. -> Mitigation: keep the detection narrow and regression-tested against the current field names used by live Seerr 3.2.0.
