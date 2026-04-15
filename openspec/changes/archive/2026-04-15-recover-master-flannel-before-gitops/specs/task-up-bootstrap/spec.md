## MODIFIED Requirements

### Requirement: task up revalidates master local networking before cluster bootstrap installs

The `configure-os` bootstrap path MUST confirm that the K3s master still has a usable local flannel subnet assignment immediately before Sealed Secrets and ArgoCD bootstrap installs begin.

#### Scenario: master flannel state regresses after the earlier networking gate

- **WHEN** the earlier node-local networking gate has already passed
- **AND** the master no longer has a usable `/run/flannel/subnet.env` by the time cluster bootstrap is about to install Sealed Secrets or ArgoCD
- **THEN** the playbook re-runs the existing bounded master flannel recovery path before those installs proceed
- **AND** if that bounded recovery path needs to restart the master `k3s` service, it first refreshes the degraded Longhorn fail-open workaround when the admission service exists with zero endpoints and still fails closed
- **AND** bootstrap fails with the existing flannel diagnostics if that bounded recovery still cannot restore the local flannel state

### Requirement: node label reconciliation does not run in the fragile pre-bootstrap window

The `configure-os` bootstrap path MUST defer custom Kubernetes node-label reconciliation until after kube-system core and ArgoCD bootstrap are stable enough for intended traffic.

#### Scenario: bootstrap reaches cluster core readiness but workload labels are still pending

- **WHEN** the playbook is still preparing Sealed Secrets or ArgoCD bootstrap
- **THEN** custom node labels are not applied yet
- **AND** the labels are reconciled only after ArgoCD bootstrap has completed successfully
