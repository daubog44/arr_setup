## 1. Spec And Docs

- [ ] 1.1 Add the delta spec for explicit Cloudflare publication from the ingress catalog
- [ ] 1.2 Update docs so wildcard tunnel publication is no longer described as acceptable behavior

## 2. Cloudflare Publication Logic

- [ ] 2.1 Derive explicit hostnames from the ingress catalog used by `verify-web`
- [ ] 2.2 Update `sync_cloudflare()` to publish only declared hostnames and end with `http_status:404`
- [ ] 2.3 Remove wildcard/apex DNS and stale managed records for undeclared hostnames

## 3. Verification

- [ ] 3.1 Run static validation (`openspec validate`, `task -n up`)
- [ ] 3.2 Run live reconcile (`task reconcile:argocd` or `task up`) and verify declared URLs still work
- [ ] 3.3 Confirm an undeclared hostname no longer routes through the tunnel
