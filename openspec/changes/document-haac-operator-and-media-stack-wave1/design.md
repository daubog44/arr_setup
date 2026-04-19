## Design

### Scope boundary

This wave is documentation-only. It should not change runtime behavior except where docs expose a real missing contract that another change already addresses.

### Documentation set

The repo should gain a stable documentation set that answers these operator questions directly:

- what `task up` really does phase by phase
- how `.env` inputs map into generated GitOps outputs
- how the media stack is wired from Seerr to downloader to NAS to Jellyfin
- which services are in scope, which are intentionally out of scope, and why
- how the security stack is layered across Cloudflare, Authelia, Kyverno, Falco, Trivy, and CrowdSec

The output should prefer a few durable guides over one giant README expansion.

### Verification

- `openspec validate document-haac-operator-and-media-stack-wave1`
- doc-path review against the implemented task surface and current code
- link consistency and command consistency checks where applicable

### Recovery and rollback

- rollback removes only the added documentation files and README links
