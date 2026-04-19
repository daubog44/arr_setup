## Why

Live ARR validation on April 19, 2026 still failed in the downloader bootstrap even after the ProtonVPN plan was active:

- Gluetun reported `make sure you have +pmp at the end of your OpenVPN username`
- the repo-managed secret generator currently normalizes `OPENVPN_USER` as `...+pmp+nr`
- Proton's current manual port-forwarding guidance says the OpenVPN username should end with `+pmp`

That makes the ARR bootstrap sensitive to an outdated credential suffix convention even when the operator has a valid paid ProtonVPN account.

## What Changes

- Normalize the generated ProtonVPN OpenVPN username so the managed port-forwarding suffix ends with `+pmp`
- Strip the legacy `+nr` suffix from repo-managed generation
- Document the operator contract so `.env` keeps the raw Proton OpenVPN username and the repo-managed secret applies the forwarding suffix

## Capabilities

### New Capabilities
- `protonvpn-port-forward-bootstrap`: Define the supported normalization contract for ProtonVPN OpenVPN usernames used by the downloader port-forwarding bootstrap.

## Impact

- Affected code will live primarily in [scripts/haac.py](C:/Users/Utente/OneDrive%20-%20ITS%20Tech%20Talent%20Factory/Desktop/dev/arr_setup-main/scripts/haac.py), [.env.example](C:/Users/Utente/OneDrive%20-%20ITS%20Tech%20Talent%20Factory/Desktop/dev/arr_setup-main/.env.example), [README.md](C:/Users/Utente/OneDrive%20-%20ITS%20Tech%20Talent%20Factory/Desktop/dev/arr_setup-main/README.md), and [tests/test_haac.py](C:/Users/Utente/OneDrive%20-%20ITS%20Tech%20Talent%20Factory/Desktop/dev/arr_setup-main/tests/test_haac.py).
- Validation must include OpenSpec validation, focused unit coverage, a full `task up` rerun so the managed secret rotates, and a live `media:post-install` rerun.
