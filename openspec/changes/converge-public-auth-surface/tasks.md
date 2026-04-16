## 1. Spec And Catalog Alignment

- [ ] 1.1 Update the `public-ui-surface` delta spec so the declared auth matrix, Headlamp OIDC contract, and browser verification fallback rules match the intended runtime behavior.
- [ ] 1.2 Confirm the ingress catalog still renders Homepage links and aliases for Litmus and ChaosTest from source templates.

## 2. Headlamp Native OIDC

- [ ] 2.1 Add Headlamp OIDC client generation and Authelia configuration, including the `/oidc-callback` redirect URI and sealed secret handling.
- [ ] 2.2 Replace the broken Headlamp OIDC attempt with the documented shared-deployment fallback: edge forward-auth plus a repo-managed in-cluster kubeconfig that removes the second login prompt.
- [ ] 2.3 Update the Headlamp deployment and route metadata so the declared auth strategy matches the live browser flow.

## 3. Verification And Reconcile

- [ ] 3.1 Tighten browser verification for the public UI surface so native OIDC routes must complete their login flow and Homepage visibly contains Litmus and ChaosTest.
- [ ] 3.2 Run static validation (`openspec validate`, `helm template`, `kubectl kustomize`, `task -n up`) and live reconcile (`task reconcile:argocd`, `task up`) until the public routes converge.
- [ ] 3.3 Run sidecar architecture and security review, fix any evidence-backed findings inside the active change, and archive the change when no findings remain.
