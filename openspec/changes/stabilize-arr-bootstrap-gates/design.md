## Context

The repo already deploys the downloader pod as a same-pod bundle of `gluetun`, `qbittorrent`, `qui`, `port-sync`, and the qBittorrent exporter. The intended steady state is:

- Gluetun reaches `Initialization Sequence Completed` and writes a forwarded port file.
- qBittorrent accepts the repo-managed password and exposes its authenticated WebUI API.
- QUI exposes `/api/auth/me`, stores a qBittorrent instance, and reports it connected.
- `port-sync` keeps syncing the forwarded port to qBittorrent.

Live inspection on April 18, 2026 showed exactly that state inside the running pod:

- Gluetun reached ProtonVPN successfully and logged `port forwarded is 61123`.
- QUI returned `200` on `/api/auth/me`.
- QUI already stored the qBittorrent instance with `"connected": true`.
- qBittorrent returned `403 Forbidden` on `/api/v2/app/version`, which is an acceptable authenticated-ready signal for this app.

Despite that, `bootstrap_downloaders_session()` still timed out and `reconcile_media_stack()` reclassified the failure as a ProtonVPN blocker because the Gluetun logs merely contained generic `openvpn` lines.

## Goals / Non-Goals

**Goals:**
- Make the downloader readiness gate succeed when the pod-local qBittorrent and QUI APIs are already healthy enough for the supported bootstrap path.
- Reserve the ProtonVPN blocker message for genuine auth/subscription/port-forwarding failures.
- Restore `media:post-install` as the supported path that can continue into Seerr/Jellyfin setup and media metrics validation.

**Non-Goals:**
- This wave does not add new ARR apps, TRaSH profiles, or additional dashboards.
- This wave does not redesign the downloader topology away from the current same-pod architecture.
- This wave does not change the operator’s ProtonVPN credentials model in `.env`.

## Decisions

### 1. Treat the downloader bootstrap as the source of truth, not a stricter pre-bootstrap probe

The current helper waits for both QUI and qBittorrent before running the real bootstrap logic, but that precondition is stricter than the supported in-pod `port-sync` bootstrap itself. The fix should let the helper validate the minimum pod-local surface required to proceed and then rely on the existing qBittorrent login / QUI instance reconciliation checks for the real readiness contract.

Rejected alternative:
- Keep the existing pre-bootstrap loop and simply increase timeouts. This would preserve a false-negative path and keep `media:post-install` nondeterministic.

### 2. Make the VPN blocker detector evidence-based

The current detector matches generic terms such as `openvpn`, which appear in healthy Gluetun logs. The detector should only escalate a Proton blocker when the recent logs show real auth, subscription, or provider-side port-forwarding failure markers, or when Gluetun never reaches the forwarded-port steady state.

Rejected alternative:
- Remove the specialized Proton blocker message entirely. That would lose useful operator guidance for the genuine bad-credentials case that already happened in previous live runs.

### 3. Keep the change narrow and bootstrap-focused

The first safe move is to restore truthful readiness and failure attribution so the rest of the ARR automation can be built on top of a trustworthy `media:post-install` surface.

Rejected alternative:
- Combine this with Seerr/TRaSH/new-app work in the same wave. That would mix unblock work with feature expansion and make rollback or diagnosis harder.

## Risks / Trade-offs

- [Risk] A looser pre-bootstrap readiness check could mask a real qBittorrent startup regression. → Mitigation: keep the later explicit qBittorrent login check and QUI connectivity test as the actual acceptance gate.
- [Risk] Tightening the VPN blocker matcher could miss a new Proton failure string. → Mitigation: match multiple concrete failure families and keep the raw last log lines in the raised error path when a true blocker is detected.
- [Risk] The live cluster can still expose transient WSL tunnel failures while validating the fix. → Mitigation: preserve focused unit coverage and use the repo-supported `cluster_session()` path for live validation.
