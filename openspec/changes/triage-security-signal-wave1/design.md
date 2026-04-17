## Design

### Severity model

This wave will treat security findings in four buckets:

- **Urgent and fix now**: repo-managed workloads in `baseline` or `restricted` namespaces that violate the current Kyverno baseline, plus custom Falco rules that create alert floods.
- **Urgent migration residue**: zero-replica historical ReplicaSets from pre-fix rollouts that keep Kyverno Policy Reporter red even after the active workload has become compliant.
- **Actionable but not blanket-fixed in this wave**: Trivy image CVEs on user-facing workloads where newer image tags or vendor fixes may exist, but the remediation path needs controlled upgrades rather than blind image churn.
- **Expected homelab tradeoff noise**: policy-style findings produced by Trivy against namespaces intentionally labeled `pod-security.kubernetes.io/enforce=privileged`, where the repo has already declared an exception model.

### Kyverno resource compliance

The current baseline already requires requests and limits in `baseline` and `restricted` namespaces. Instead of weakening that policy, this wave will patch the repo-managed workloads that currently violate it:

- Argo CD control-plane components in `argocd`, with the active defect narrowed to the `argocd-redis` init-container path
- Falcosidekick and Falcosidekick UI in `security`
- Litmus MongoDB in `chaos`

The resource shapes will be conservative so the single-master control plane remains within the capacity work already completed.

Because Policy Reporter also scans historical rollout objects, the live cleanup path for this wave may delete zero-replica ReplicaSets that were generated before the resource patches existed. That cleanup is migration-only residue handling, not a weakening of the policy baseline.

### Falco noise reduction

The current custom host rule fires on any `nc`, `ncat`, or `socat` spawn. The live noise comes from loopback-only probe traffic, not lateral movement. The rule will therefore be narrowed to ignore obvious localhost/127.0.0.1 probes while preserving warnings for non-loopback socket tooling.

The post-install security playbook remains the source of truth for delivering the host rule bundle.

### Trivy signal quality

Trivy vulnerability scanning remains enabled. This wave only changes the policy-style reporting path:

- keep vulnerability reports and Prometheus metrics enabled
- record only failed config-audit and RBAC-style checks
- keep the scanner scope unchanged for now so the operator can still see CVEs on published workloads

This preserves real CVE visibility while making Grafana and Policy Reporter counts closer to things to fix instead of all checks ever recorded.

The remaining image CVE backlog is not treated as noise. When triage shows that critical or high counts are concentrated on repo-managed published services, this wave must open a separate remediation change instead of silently accepting the backlog.

### Verification

- `openspec validate triage-security-signal-wave1`
- `python scripts/haac.py check-env`
- `python scripts/haac.py doctor`
- `python scripts/haac.py task-run -- -n up`
- `python -m py_compile scripts/haac.py scripts/haac_loop.py scripts/hydrate-authelia.py`
- `python -m unittest discover -s tests -p "test_haac.py" -v`
- `helm template haac-stack k8s/charts/haac-stack`
- `kubectl kustomize k8s/bootstrap/root`
- `kubectl kustomize k8s/platform`
- `kubectl kustomize k8s/workloads`
- `python scripts/haac.py task-run -- reconcile:gitops`
- live cluster check that active Kyverno failures for requests/limits are cleared in `argocd`, `security`, and `chaos`
- one-time live cleanup of zero-replica historical ReplicaSets if those older rollout objects are the only remaining source of Kyverno failures
- browser validation for Grafana, Falco, and Kyverno
