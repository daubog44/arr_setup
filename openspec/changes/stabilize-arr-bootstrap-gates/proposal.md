## Why

`media:post-install` is currently not a reliable operator path even when the media stack is actually healthy. Live verification on April 18, 2026 showed the `downloaders` pod reaching ProtonVPN, obtaining a forwarded port, and connecting QUI to qBittorrent, while the Python bootstrap still failed with `QUI API did not become available before timeout` and then misreported the failure as a ProtonVPN subscription problem.

## What Changes

- Stabilize the downloader bootstrap readiness gate so it reflects the actual healthy contract of the `downloaders` pod instead of timing out on a fragile early probe.
- Narrow the ProtonVPN blocker classifier so media bootstrap only reports a VPN credential/subscription failure when the live Gluetun evidence actually proves it.
- Reuse the supported downloader bootstrap path to validate qBittorrent and QUI connectivity after the pod is already rolled out, rather than failing before the real bootstrap logic can confirm readiness.
- Add focused regression coverage for the downloader readiness and failure-classification paths.

## Capabilities

### New Capabilities

- `arr-bootstrap-readiness`: Define the stable readiness and failure-reporting contract for the downloader portion of the repo-managed ARR stack.

### Modified Capabilities

- `task-up-bootstrap`: `task up` failure attribution must distinguish a real ProtonVPN blocker from a downloader API readiness failure inside `media:post-install`.

## Impact

- Affected code lives in [scripts/haac.py](C:/Users/Utente/OneDrive%20-%20ITS%20Tech%20Talent%20Factory/Desktop/dev/arr_setup-main/scripts/haac.py), [tests/test_haac.py](C:/Users/Utente/OneDrive%20-%20ITS%20Tech%20Talent%20Factory/Desktop/dev/arr_setup-main/tests/test_haac.py), and potentially the downloader chart if the supported bootstrap contract needs the pod-local script aligned with the Python helper.
- Verification must include OpenSpec validation, targeted Python unit tests, a live `media:post-install` rerun, and browser verification of Seerr once media bootstrap can proceed past downloader readiness.
