## Why

The new CrowdSec plus Traefik AppSec layer protects the public ingress path, but real operator verification now triggers false positives severe enough to ban the operator IP and turn the entire public surface into `403`.

The evidence is concrete:

- CrowdSec decisions show `LePresidente/http-generic-403-bf` bans for the current operator IP.
- CrowdSec AppSec alerts show out-of-band matches on supported operator and media paths such as Ntfy topics, Jellyfin playback progress, and Grafana auxiliary SPA APIs.
- A healthy cluster can therefore fail the public-route gate purely because CrowdSec treats expected operator traffic as hostile.

This must be fixed narrowly and declaratively instead of relying on manual ban clearing or disabling CrowdSec wholesale.

## What Changes

- Add repo-managed CrowdSec parser whitelists for the exact access-log events that are known-good and currently create false-positive `403` brute-force style bans.
- Add a repo-managed custom AppSec config that allows and suppresses alerts for the exact supported homelab operator paths already proven to false-positive.
- Keep the protection model honest: CrowdSec still protects the wider ingress path, while the documented operator/browser verification traffic is no longer treated as an attack.
- Validate the change by re-running public URL verification and then the broader acceptance wave.

## Capabilities

### New Capabilities
- `crowdsec-operator-false-positive-control`: Repo-managed suppression of proven false positives on supported operator and media UI paths without disabling the general CrowdSec ingress protection layer.

### Modified Capabilities
- `public-ui-surface`: Public-route verification must remain compatible with the declared CrowdSec protection model.
- `task-up-idempotence`: The public URL verification phase must not fail solely because the repo-managed verifier traffic is misclassified by CrowdSec.

## Impact

- Affected code lives in `k8s/platform/applications/crowdsec-app.yaml.template`, `scripts/haac.py`, `tests/test_haac.py`, and the security docs.
- Validation must include OpenSpec, Python/test gates, a live CrowdSec reconcile, and a real rerun of public URL verification.
