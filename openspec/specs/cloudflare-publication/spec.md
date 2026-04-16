# cloudflare-publication Specification

## Purpose
Define the stable Cloudflare publication contract so tunnel ingress and DNS records are derived only from the declared ingress catalog and undeclared hosts are not internet-routable.
## Requirements
### Requirement: Cloudflare publication derives from the ingress catalog

The repo MUST publish only the explicitly declared public hostnames through Cloudflare.

#### Scenario: explicit tunnel ingress publication

- **WHEN** Cloudflare tunnel configuration is reconciled
- **THEN** each enabled ingress entry in the catalog MUST publish exactly `<subdomain>.<domain>`
- **AND** the tunnel configuration MUST NOT publish `*.${DOMAIN_NAME}` as a wildcard catch-all
- **AND** the tunnel configuration MUST NOT publish `${DOMAIN_NAME}` as an apex catch-all unless it is explicitly declared in the catalog
- **AND** the final tunnel ingress rule MUST remain `http_status:404`

#### Scenario: explicit DNS publication

- **WHEN** Cloudflare DNS is reconciled
- **THEN** each declared public hostname MUST exist as a proxied CNAME to the active tunnel target
- **AND** wildcard or apex records created only for legacy catch-all publication MUST be removed
- **AND** stale managed DNS records for undeclared hostnames under the managed domain MUST be removed

#### Scenario: undeclared hostnames are not routable

- **WHEN** a hostname under the managed domain is not declared in the ingress catalog
- **THEN** the tunnel MUST NOT route it to Traefik
- **AND** the request MUST fall through to the tunnel `http_status:404` rule
