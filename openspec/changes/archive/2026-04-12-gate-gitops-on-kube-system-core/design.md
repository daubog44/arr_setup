## Context

The current live rerun after `bound-flannel-cni-recovery` already proves two useful facts:

- the local node-side flannel helper now stops at the correct boundary and emits combined node-local plus cluster-side evidence
- the next missing capability is not another local node restart path, but a cluster-side readiness contract before GitOps bootstrap

The existing node `Ready` gate is too weak. A node can be registered and still fail to run core pods because cluster-side flannel is absent or essential `kube-system` deployments have not converged.

## Goals / Non-Goals

**Goals**

- Preserve the current `Node configuration` failure boundary.
- Refuse to enter GitOps bootstrap until cluster-side flannel shows one Ready pod per K3s node.
- Refuse to enter GitOps bootstrap until essential `kube-system` deployments prove the cluster can start core pods.
- Fail Sealed Secrets rollout with controller-specific evidence if it still does not converge after the stronger pre-bootstrap gate.

**Non-Goals**

- Repair intermittent workstation-to-worker SSH failures.
- Replace flannel or redesign the K3s networking stack.
- Add indefinite retries or hide failure behind best-effort loops.

## Decisions

### Add a master-side cluster flannel gate before GitOps bootstrap

The live failure now proves local `/run/flannel/subnet.env` checks are necessary but not sufficient. The master must also confirm that the cluster-side flannel workload is present and Ready across the full K3s node set before the bootstrap can trust normal pod startup.

The intended shape is:

- run the gate from the master after the existing node `Ready` check
- require one Ready flannel pod per expected K3s node
- attempt one bounded delete of non-ready flannel pods if the cluster-side flannel gate does not converge
- fail with daemonset, pod, and event diagnostics if that bounded recovery still fails

### Add an essential `kube-system` deployment gate

Even if flannel recovers, GitOps bootstrap should not begin until a small set of core cluster deployments can actually roll out.

The intended shape is:

- gate on `coredns`, `local-path-provisioner`, and `metrics-server`
- stop before Sealed Secrets if those deployments do not converge
- emit deployment, pod, and event diagnostics from `kube-system`

### Narrow Sealed Secrets failures to the controller itself

If the stronger pre-bootstrap gates pass but Sealed Secrets still times out, the operator needs direct controller evidence rather than a generic rollout timeout.

The intended evidence bundle is:

- `kubectl get deploy sealed-secrets-controller -n kube-system -o wide`
- matching Sealed Secrets pod list
- `kubectl describe pod` for matching pods
- controller logs
- recent `kube-system` events

## Risks / Trade-offs

- The stronger gate may stop bootstrap earlier and more often.
  - Acceptable. Earlier explicit failure is better than proceeding into later GitOps noise with a cluster that cannot run core pods.
- The bounded delete of non-ready flannel pods may still not recover the cluster.
  - Acceptable. The goal is to expose the correct remaining blocker, not to guarantee a full self-heal in one step.
