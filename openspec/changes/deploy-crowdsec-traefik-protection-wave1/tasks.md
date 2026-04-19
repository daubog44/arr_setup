## 1. Contracts

- [ ] 1.1 Add OpenSpec deltas for CrowdSec ingress remediation and the Cloudflare versus CrowdSec responsibility split
- [ ] 1.2 Define the secret and middleware contract for the Traefik bouncer path

## 2. Implementation

- [ ] 2.1 Add the CrowdSec platform application, namespace, secrets, and supported chart values
- [ ] 2.2 Wire Traefik access-log acquisition and the bouncer middleware with AppSec enabled
- [ ] 2.3 Add observability and docs for CrowdSec metrics or explicitly record any supported limitations
- [ ] 2.4 Add focused tests for rendered config, middleware, and secret generation

## 3. Validation

- [ ] 3.1 Validate with OpenSpec, render gates, and a live platform reconcile
- [ ] 3.2 Prove that a known bad request is blocked through the Traefik plus CrowdSec path
