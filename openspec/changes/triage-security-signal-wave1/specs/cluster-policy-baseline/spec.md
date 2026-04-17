## MODIFIED Requirements

### Requirement: Cluster policy baseline is repo-managed
The repository MUST manage a baseline Kubernetes policy layer instead of relying only on app-by-app hardening.

#### Scenario: Repo-managed baseline namespaces stay compliant

- **WHEN** the platform layer reconciles repo-managed workloads into namespaces labeled `pod-security.kubernetes.io/enforce=baseline` or `restricted`
- **THEN** those workloads MUST satisfy the repo-managed Kyverno baseline policies without requiring operator-side manual exemptions
- **AND** violations caused by missing resource requests or limits MUST be fixed in the workload manifests rather than silenced in Policy Reporter
