## MODIFIED Requirements

### Requirement: Security baseline documents ingress remediation boundaries

The repo security baseline MUST describe where ingress remediation happens and where it does not.

#### Scenario: The operator reads the security model

- **WHEN** the repo documents the cluster security posture
- **THEN** it MUST explain that CrowdSec covers in-cluster request-level remediation and AppSec
- **AND** it MUST explain that large volumetric DDoS mitigation remains primarily an upstream edge responsibility rather than a cluster-only guarantee

