# Design

## Scope

This change only touches the Cloudflare publication boundary:

- tunnel ingress rules
- DNS records that point the domain to the tunnel
- docs/spec language describing publication behavior

It does not change the in-cluster Gateway/HTTPRoute model.

## Source Of Truth

The existing ingress catalog under `k8s/charts/haac-stack/config-templates/values.yaml.template` remains the single source of truth for public hostnames. Cloudflare publication must derive from the same catalog used by:

- Homepage rendering
- `verify-web`
- route auth metadata

## Publication Model

For each enabled ingress entry:

- publish `<subdomain>.<domain>` through the tunnel to Traefik
- create or reconcile a proxied CNAME record to `<tunnel-id>.cfargotunnel.com`

For undeclared hosts:

- do not publish wildcard or apex catch-alls
- end the tunnel ingress config with `http_status:404`

## Reconciliation Rules

- preserve unrelated tunnel ingress entries that are not part of the managed domain
- remove managed wildcard/apex entries
- remove managed DNS records for hostnames that are no longer declared
- keep only declared hostnames for the managed domain pointed at the tunnel target

## Verification

- `verify-web` remains catalog-driven and therefore already aligned
- live validation must include `task reconcile:argocd` or `task up`
- a spot check of an undeclared hostname should no longer reach Traefik through the wildcard tunnel
