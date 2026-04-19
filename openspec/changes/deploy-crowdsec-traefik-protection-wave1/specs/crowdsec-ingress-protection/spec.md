## ADDED Requirements

### Requirement: Ingress remediation is repo-managed

The repo MUST provide a supported in-cluster ingress remediation path for behavior-based blocking and AppSec inspection on the published Traefik routes.

#### Scenario: CrowdSec protects the Traefik edge

- **WHEN** the platform is reconciled
- **THEN** CrowdSec MUST be deployed in-cluster with a repo-managed configuration for Kubernetes and Traefik acquisition
- **AND** Traefik MUST enforce CrowdSec decisions through a supported bouncer middleware path

