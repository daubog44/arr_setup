## 1. Public surface contract

- [ ] 1.1 Change the Litmus ingress catalog entry to `app_native`
- [ ] 1.2 Remove the `ChaosTest` Homepage alias from the Litmus route
- [ ] 1.3 Update the stable public UI spec so Litmus is a single canonical app-native route

## 2. Repo-managed Litmus auth

- [ ] 2.1 Add repo-managed Litmus admin credentials derived from operator inputs
- [ ] 2.2 Publish the Litmus admin sealed secret into the `chaos` namespace
- [ ] 2.3 Point the Litmus chart at the existing secret instead of the chart default

## 3. Verification

- [ ] 3.1 Update browser verification to fail if Litmus still shows a broken or duplicate login flow
- [ ] 3.2 Reconcile the cluster and prove Homepage shows one Litmus entry and browser login succeeds
- [ ] 3.3 Validate the change with OpenSpec, Helm, Kustomize, `task -n up`, and live verification
