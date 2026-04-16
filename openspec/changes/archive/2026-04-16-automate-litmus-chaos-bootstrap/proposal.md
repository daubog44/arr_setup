## Why

Litmus login and auth are now automated, but the default chaos environment still stops on a manual operator step: the UI asks the operator to download a generated YAML file and apply it to the cluster by hand. That violates the repository contract that `task up` is the product and that post-bootstrap reconciliation should not depend on ad hoc UI work.

## What Changes

- add a Litmus chaos bootstrap reconciler that:
  - authenticates to the internal Litmus control-plane APIs
  - ensures a usable default environment exists
  - registers a default chaos infrastructure when none is active
  - applies the returned infrastructure manifest automatically to the cluster
  - waits until Litmus reports the infrastructure active and confirmed
- wire the reconciler into the existing `task up`, `reconcile:argocd`, and `reconcile:gitops` verification path
- strengthen the Litmus public-surface verification so regressions are caught before closeout

## Outcome

After `task up` or `task reconcile:gitops`, Litmus must expose a functional default environment with an active chaos infrastructure, without requiring the operator to download or apply any YAML manually.
