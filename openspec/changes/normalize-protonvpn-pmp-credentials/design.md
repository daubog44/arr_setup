## Context

The ARR stack uses Gluetun plus ProtonVPN OpenVPN credentials stored in the repo-managed `protonvpn-key` secret.

The repo already appends a forwarding suffix automatically, but the current shape is stale:

- current repo generation: `username+pmp+nr`
- live Gluetun error: `make sure you have +pmp at the end of your OpenVPN username`
- current Proton manual guidance: append `+pmp` to the OpenVPN username for port forwarding

## Goals / Non-Goals

**Goals**

- Make the generated credential shape match the current Proton manual contract
- Preserve other supported suffixes if the operator already uses them, while ensuring `pmp` stays last
- Keep `.env` ergonomic by accepting the raw OpenVPN username as operator input

**Non-Goals**

- This change does not redesign the downloader networking topology
- This change does not migrate the stack from OpenVPN to WireGuard

## Decisions

### 1. Normalize the username instead of documenting a manual suffix hack

The operator input should stay the raw Proton OpenVPN username from the Proton account page. The repo-managed secret generation should derive the forwarding-ready username.

### 2. Remove the legacy `nr` suffix

`nr` is no longer part of the supported port-forwarding contract in the current Proton guidance used for this homelab. The generator should strip it if present.

### 3. Keep `pmp` last

If the operator uses another supported Proton suffix, the repo-managed normalizer should keep it but ensure the final suffix order ends in `+pmp`.

## Risks / Trade-offs

- If Proton changes the suffix contract again, the normalizer may need another targeted wave.
- Rotating the managed secret requires a real GitOps reconciliation, so validation must include a live rerun rather than only unit tests.
