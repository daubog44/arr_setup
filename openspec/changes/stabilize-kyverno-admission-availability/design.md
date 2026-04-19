## Summary

Kyverno blocks admission for repo-managed resources. A single replica is acceptable for a lab demo, but not for a bootstrap path that treats `task up` as the supported rerun contract. The minimum safe improvement is two admission replicas with scheduling guidance that biases them onto different nodes.

## Design

### Replica topology

- Set `admissionController.replicas` to `2`.
- Keep the chart defaults for anti-affinity enabled.
- Add a `topologySpreadConstraints` entry on `kubernetes.io/hostname` so the scheduler prefers one pod per node when capacity exists.
- Enable or preserve a disruption budget with at least one available pod during voluntary disruptions.

### Scope

- Only the admission controller is in scope for this change. Background, cleanup, and reports controllers can remain single replica because they do not front synchronous admission traffic.
- No policy semantics change in this wave.

### Rollback

- Revert the Kyverno values back to single replica and remove the spread rule.
- Rerun ArgoCD sync for the Kyverno application if the chart change causes an unexpected scheduling issue.
