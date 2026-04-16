# explicit-cloudflare-publication

## Why

`sync_cloudflare()` still publishes the homelab through wildcard and apex catch-all records (`*.domain` and `domain`). That means any future hostname under the zone becomes internet-routable through the tunnel without first being declared in the repo source of truth.

The repo already has a single ingress catalog under `values.yaml.template` that drives HTTP-level verification and Homepage rendering. Cloudflare publication should derive from that same catalog instead of a wildcard.

## What Changes

- derive Cloudflare tunnel ingress rules from the declared ingress catalog
- publish only explicitly declared hostnames
- remove wildcard and apex catch-all publication from Cloudflare tunnel configuration and DNS
- keep a final `http_status:404` tunnel fallback so undeclared hosts are not routable
- keep URL verification aligned to the same explicit catalog

## Acceptance Criteria

- `sync_cloudflare()` no longer publishes `*.${DOMAIN_NAME}` or `${DOMAIN_NAME}` unless the hostname is explicitly declared
- undeclared hosts under the domain resolve to Cloudflare 404 instead of reaching Traefik
- declared public URLs continue to pass `verify-web`
- `task up` remains green with the new Cloudflare publication model
