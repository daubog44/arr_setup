## ADDED Requirements

### Requirement: Security dashboards must separate urgent defects from declared homelab tradeoffs

The operator surface MUST distinguish between repo-managed security defects that should be fixed immediately and findings that are expected because the repo intentionally grants elevated behavior to specific homelab namespaces.

#### Scenario: Kyverno baseline fails in baseline or restricted namespaces

- **WHEN** Kyverno reports baseline-policy failures in namespaces labeled `pod-security.kubernetes.io/enforce=baseline` or `restricted`
- **THEN** those failures MUST be treated as urgent repo defects
- **AND** the repo MUST prefer patching the affected workloads instead of weakening the baseline policy

#### Scenario: Trivy reports findings for privileged namespaces

- **WHEN** Trivy reports policy-style findings for workloads in namespaces intentionally labeled `pod-security.kubernetes.io/enforce=privileged`
- **THEN** the operator surface MAY classify those findings as expected homelab tradeoffs
- **AND** that classification MUST NOT disable vulnerability scanning for published workloads
