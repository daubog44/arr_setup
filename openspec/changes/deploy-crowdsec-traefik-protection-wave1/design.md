## Design

### Scope boundary

This wave adds behavior-based ingress protection and AppSec to the existing cluster. It does not claim to replace an upstream volumetric DDoS service and it does not remove Cloudflare from the current edge path.

### Protection model

The supported enforcement layers are:

1. Cloudflare at the public edge for large-scale DDoS absorption and network-level shielding
2. Traefik middleware remediation in-cluster for request-level blocking and captcha or deny actions
3. CrowdSec Security Engine plus Local API for detection, decisions, and AppSec analysis

That means the repo should document "total DDoS protection" carefully: the cluster can meaningfully improve layer-7 abuse handling, bot and brute-force reactions, and virtual patching, but it cannot absorb a true volumetric attack by itself.

### Kubernetes deployment

The repo should use the official CrowdSec Helm chart and keep secrets out of tracked values.

The intended topology is:

- one `crowdsec` namespace
- in-cluster CrowdSec Security Engine and LAPI
- Traefik acquisition so access logs are parsed with the right `program: traefik` contract
- Traefik bouncer plugin middleware with AppSec enabled
- a generated secret for bouncer keys and enrollment material

The design should keep SQLite out of any "highly available" claim and stay honest about homelab scale. If the chart default remains SQLite, the docs must describe the limitation plainly.

### Verification

- `openspec validate deploy-crowdsec-traefik-protection-wave1`
- `helm template`
- `kubectl kustomize k8s/platform`
- live ArgoCD reconcile
- AppSec verification through a benign blocked probe such as requesting `/.env` behind Traefik and confirming a block decision

### Recovery and rollback

- `task up` remains the full recovery path for platform reconcile
- rollback removes CrowdSec and Traefik middleware without disturbing Cloudflare publication
