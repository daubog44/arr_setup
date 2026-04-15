## MODIFIED Requirements

### Requirement: Repo-Owned ArgoCD Bootstrap

The first bootstrap of ArgoCD MUST come from repo-local manifests, not a remote install URL.

#### Scenario: Fresh cluster bootstrap

- **WHEN** `deploy-argocd` bootstraps ArgoCD on a fresh cluster
- **THEN** it MUST apply the vendored local bootstrap manifests from the repo into the `argocd` namespace on the first apply
- **AND** it MUST NOT create a second namespaced ArgoCD install in `default`
- **AND** the self-management GitOps application MUST take over afterward

#### Scenario: Legacy bootstrap drift exists in default namespace

- **WHEN** an earlier bootstrap created ArgoCD resources in `default`
- **THEN** the reconciliation path MUST remove that legacy install after the repo-owned `argocd` install is healthy
