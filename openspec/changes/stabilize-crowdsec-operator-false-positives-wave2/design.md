## Design

### Scope boundary

This wave does not weaken CrowdSec globally and does not remove AppSec from Traefik. It only suppresses already-proven false positives for supported operator and media UI traffic.

### Failure chain

The current failure path is:

1. supported operator traffic hits routes that legitimately return `403` or trigger low-confidence AppSec anomaly matches
2. CrowdSec converts those events into alerts and, for some scenarios, into real bans
3. the Traefik bouncer then blocks every public route for the operator IP
4. `verify-web` and the final `task up` public-route phase fail even though the cluster is healthy

The fix must break the chain before the decision is created.

### Suppression model

Two narrow layers are required:

1. parser whitelist for exact access-log events
   - used for known-good `403` access-log events that should never reach generic scenarios like `LePresidente/http-generic-403-bf`
   - examples include the known Ntfy topic posts, Jellyfin playback progress, and specific Grafana auxiliary API routes
2. AppSec custom config hooks
   - used where the AppSec engine itself is the source of the false positive
   - the custom config should use request filters on `req.Host` and `req.URL.Path`
   - the action should be `SetRemediation("allow")` plus `CancelAlert()` so the request is allowed and no noisy alert remains

### Configuration shape

The CrowdSec Helm chart already supports:

- `config.parsers.s02-enrich`
- `appsec.configs`

The repo should therefore inject:

- one narrow parser-whitelist file for the exact access-log patterns
- one custom AppSec config file appended after `crowdsecurity/appsec-default`

### Verification

- `openspec validate stabilize-crowdsec-operator-false-positives-wave2`
- `python -m py_compile scripts/haac.py tests/test_haac.py`
- targeted unit tests for the rendered CrowdSec contract
- `python scripts/haac.py task-run -- wait-for-argocd-sync`
- `python scripts/haac.py verify-web --domain <domain> --master-ip ... --proxmox-host ... --kubeconfig ... --kubectl ...`
- `node scripts/verify-public-auth.mjs`

### Recovery and rollback

- rollback removes the custom whitelist and AppSec hook files while leaving CrowdSec installed
- until the reconcile is live, manual ban clearing plus Traefik restart remains only a temporary recovery, not the final contract
