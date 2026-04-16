## 1. Spec And Catalog Alignment

- [x] 1.1 Update the `public-ui-surface` delta spec so the declared auth matrix, Headlamp OIDC contract, and browser verification fallback rules match the intended runtime behavior.
- [x] 1.2 Confirm the ingress catalog still renders Homepage links and aliases for Litmus and ChaosTest from source templates.

## 2. Headlamp Native OIDC

- [x] 2.1 Remove stale Headlamp OIDC client and secret artifacts, and replace them with the documented shared-deployment fallback.
- [x] 2.2 Replace the broken Headlamp OIDC attempt with edge forward-auth plus a repo-managed in-cluster kubeconfig that removes the second login prompt.
- [x] 2.3 Update the Headlamp deployment and route metadata so the declared auth strategy, Authelia protection, and repo-managed access level match the live browser flow.

## 3. Verification And Reconcile

- [x] 3.1 Tighten browser verification for the public UI surface so native OIDC routes must complete their login flow and Homepage visibly contains Litmus and ChaosTest.
- [x] 3.2 Run static validation (`openspec validate`, `helm template`, `kubectl kustomize`, `task -n up`) and live reconcile (`task reconcile:argocd`, `task up`) until the public routes converge.
- [x] 3.3 Run sidecar architecture and security review, fix any evidence-backed findings inside the active change, and archive the change when no findings remain.
