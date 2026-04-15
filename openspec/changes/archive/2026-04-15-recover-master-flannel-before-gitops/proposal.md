## Why

`task up` still fails in the `configure-os` bootstrap path even after the earlier networking-gate fixes.

The new concrete evidence is:

- the master can pass the first networking gate and still lose `/run/flannel/subnet.env` before cluster-side bootstrap installs
- when that happens, pod sandbox creation on the master fails with `failed to load flannel 'subnet.env'`
- Sealed Secrets rollout then times out as a downstream symptom, even if the controller eventually lands on a worker

That means the bootstrap path still has one timing gap between "node-local networking looked good enough" and "cluster-side bootstrap begins".

## What Changes

- re-check master local flannel state immediately before Sealed Secrets and ArgoCD bootstrap installs
- refresh the degraded Longhorn fail-open workaround immediately before any bounded master `k3s` restart that is trying to rebuild local flannel state
- defer custom Kubernetes node-label reconciliation until after kube-system core and ArgoCD bootstrap are stable
- keep the recovery bounded and diagnostics-first by reusing the existing `wait_for_flannel_subnet_env.yml` task

## Impact

- `configure-os` should stop entering cluster bootstrap while the master CNI state is already degraded
- reruns of `task up` should become more deterministic because label mutations no longer happen before the bootstrap core is stable
- Sealed Secrets and ArgoCD failures should reflect real later issues instead of a hidden master flannel regression
