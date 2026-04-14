## Why

`task up` still fails during the Ansible bootstrap path because the K3s networking readiness gates are not aligned with the actual cluster behavior.

Two concrete mismatches exist:

- the local node-side readiness issue is `/run/flannel/subnet.env` missing, not a missing cluster-side flannel pod recovery path
- the post-node bootstrap gate still assumes cluster-visible flannel daemonsets or pods that this K3s layout does not expose as a stable contract
- reruns can inherit a broken Longhorn admission webhook from previous cluster state, and that fail-closed webhook can block the node mutations K3s performs while trying to recover

That leaves `configure-os` failing before GitOps bootstrap and makes later errors, including Sealed Secrets rollout failures, hard to interpret.

## What Changes

- make the K3s networking readiness path explicit and bounded around the local node contract that actually exists
- remove cluster-side flannel pod assumptions from the pre-GitOps gate
- temporarily relax degraded Longhorn admission webhooks during bootstrap recovery when the service has no endpoints
- perform one coordinated K3s service bounce after that Longhorn recovery path so nodes can rebuild local flannel runtime state
- capture targeted diagnostics when a node still cannot rebuild its local flannel state
- verify `configure-os` progresses through the corrected readiness gates without regressing the earlier idempotence work

## Impact

- `task up` and `configure-os` should fail earlier and more precisely when K3s networking is broken
- reruns should become more deterministic because bootstrap gates reflect the real cluster contract
- later GitOps failures should be interpreted from cleaner upstream evidence
