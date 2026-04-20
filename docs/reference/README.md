# Reference Guides

This directory is the stable reference set for the repo-managed operator contract.

Use these guides when `README.md` is no longer enough and you need the detailed behavior behind `task up`, the media automation flow, or the layered security posture.

## Guides

- [operator-bootstrap.md](./operator-bootstrap.md): what `task up` does phase by phase, how `.env` maps into generated outputs, and which rerun paths are supported.
- [media-stack.md](./media-stack.md): how Seerr, Prowlarr, Radarr, Sonarr, Lidarr, Whisparr, download clients, NAS storage, and Jellyfin interact in this repo.
- [security-stack.md](./security-stack.md): how Cloudflare, Authelia, Kyverno, Falco, Trivy, and CrowdSec layer together and where each control stops.

## When To Read Which Guide

- Read `operator-bootstrap.md` before touching `task up`, `task down`, or the generated GitOps artifacts.
- Read `media-stack.md` before changing the `*arr` suite, the downloader path, naming, languages, or Seerr/Jellyfin bootstrap behavior.
- Read `security-stack.md` before changing ingress, authentication, policy enforcement, runtime detection, or request blocking.
