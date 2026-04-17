## ADDED Requirements

### Requirement: Generated GitOps outputs are staged together

The system MUST stage every repo-managed generated GitOps artifact before commit/push so publication cannot silently omit regenerated platform files.

#### Scenario: Platform secrets are regenerated before publication

- **WHEN** `scripts/haac.py` regenerates repo-managed secrets and manifests for publication
- **THEN** the staging set MUST include the chart secret directory plus generated outputs outside that directory
- **AND** generated platform files such as the ArgoCD OIDC SealedSecret and the Litmus admin SealedSecret MUST be eligible for commit in the same publication run
