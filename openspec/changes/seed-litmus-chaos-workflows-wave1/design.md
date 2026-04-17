## Design

### Integration point

The existing `reconcile_litmus_chaos()` path is already the canonical imperative bridge between GitOps-managed installation and Litmus API state. This wave extends that same path instead of adding a second bootstrap job or a second operator-visible manual flow.

### Catalog shape

The first catalog will stay deliberately small and low-blast-radius:

- a management-path pod-delete template for `homepage`
- a notification-path pod-delete template for `ntfy`
- a media-path pod-delete template for `radarr`

These templates will be preconfigured and visible in ChaosCenter, but they will not be auto-scheduled. The operator can choose when to run them from the Litmus UI.

### Upstream experiment manifests

The workflow templates depend on the upstream Litmus pod-delete experiment bundle. The repo will therefore vendor the minimal upstream experiment manifest required for `pod-delete` and apply it into the Litmus control namespace during the same reconcile path.

### API contract

Official ChaosCenter GraphQL documentation states that:

- `createWorkflowTemplate` saves a workflow template in the project
- `listWorkflowManifests` lists the saved templates
- `manifest` is supplied as an escaped JSON string containing workflow YAML

This wave will use that contract to upsert templates by name instead of forcing the user to import YAML through the browser.

### Verification

- `openspec validate seed-litmus-chaos-workflows-wave1`
- `python scripts/haac.py check-env`
- `python scripts/haac.py doctor`
- `python scripts/haac.py task-run -- -n up`
- `python -m py_compile scripts/haac.py scripts/haac_loop.py scripts/hydrate-authelia.py`
- `python -m unittest discover -s tests -p "test_haac.py" -v`
- `kubectl kustomize k8s/platform`
- `python scripts/haac.py task-run -- reconcile:gitops`
- live Litmus API verification that the expected templates exist
- browser verification that Litmus authenticates and reaches an already-seeded workflow surface
