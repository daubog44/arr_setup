# task-up-bootstrap Delta

## MODIFIED Requirements

### Requirement: Repo-Owned ArgoCD Bootstrap

The first bootstrap of ArgoCD MUST come from repo-local manifests, not a remote install URL.

#### Scenario: Fresh cluster bootstrap

- **WHEN** `deploy-argocd` bootstraps ArgoCD on a fresh cluster
- **THEN** it MUST apply the vendored local bootstrap manifests from the repo
- **AND** those manifests MUST converge only in namespace `argocd`
- **AND** the self-management GitOps application MUST take over afterward

#### Scenario: Legacy default-namespace install exists

- **WHEN** a previous bootstrap left namespaced `argocd-*` resources in `default`
- **THEN** the repo-local bootstrap MUST remove those legacy namespaced resources during reconcile
- **AND** the cluster MUST converge on a single namespaced ArgoCD install in `argocd`
