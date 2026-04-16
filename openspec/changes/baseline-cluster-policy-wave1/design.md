## Design

### Kyverno baseline

This wave will use a small, high-signal baseline rather than an aggressive policy wall. The initial target set is:

- require `runAsNonRoot` where practical
- block privileged containers except explicit exceptions
- require `allowPrivilegeEscalation: false`
- require resource requests and limits
- block `:latest` tags

### Policy Reporter UI

Kyverno itself does not ship a first-class end-user dashboard. The in-cluster UI for this repo will therefore be Policy Reporter with the Kyverno plugin enabled, published through the same catalog and auth model as the rest of the control-plane surface.

### Namespace labels

Pod Security Admission labels will be applied repo-side at namespace creation time, with explicit exceptions for namespaces that truly need elevated privileges such as storage, observability, or device/runtime components.

### Falco rules

Falco already runs on the supported host-side sensor path. This wave adds:

- a repo-managed rule bundle for common homelab abuse paths
- a post-install security step that keeps the rule bundle present and aligned with the cluster-side alert pipeline

### Verification

- `openspec validate baseline-cluster-policy-wave1`
- `python scripts/haac.py task-run -- -n up`
- `& .\.tools\windows-amd64\bin\helm.exe template haac-stack k8s\charts\haac-stack`
- `& .\.tools\windows-amd64\bin\kubectl.exe kustomize k8s\bootstrap\root`
- `& .\.tools\windows-amd64\bin\kubectl.exe kustomize k8s\platform`
