## Design

### Integration point

The existing `reconcile_litmus_chaos()` path is already the canonical imperative bridge between GitOps-managed installation and Litmus API state. This wave extends that same path instead of adding a second bootstrap job or a second operator-visible manual flow.

Because the persisted Litmus auth database can drift from the repo-managed secret, the post-install task must also reconcile the admin login before it tries to seed saved experiments. That repair remains part of the same Litmus bootstrap path rather than a separate manual recovery step.

### Catalog shape

The first catalog will stay deliberately small and low-blast-radius:

- a management-path pod-delete experiment for `homepage`
- a notification-path pod-delete experiment for `ntfy`
- a media-path pod-delete experiment for `radarr`

These experiments will be preconfigured and visible in ChaosCenter, but they will not be auto-scheduled. The operator can choose when to run them from the Litmus UI.

### Upstream experiment manifests

The saved experiments depend on the upstream Litmus pod-delete experiment bundle. The repo will therefore vendor the minimal upstream `ChaosExperiment` manifest required for `pod-delete` and apply it into the Litmus control namespace during the same reconcile path.

Wave1 treats those supporting `ChaosExperiment` objects as intentionally imperative bootstrap state. They are validated as catalog-local `ChaosExperiment` manifests targeting the `litmus` namespace, but they are not pruned automatically if an entry is removed from the catalog later.

### API contract

The live ChaosCenter build exposed by chart `3.28.0` uses:

- `saveChaosExperiment` to create or update a saved project experiment
- `listExperiment` to list those saved experiments
- `manifest` as a JSON string representing a supported object such as `ChaosEngine`

This wave will use that contract to upsert experiments by name instead of forcing the user to import YAML through the browser.

### Verification

- `openspec validate seed-litmus-chaos-workflows-wave1`
- `python scripts/haac.py check-env`
- `python scripts/haac.py doctor`
- `python scripts/haac.py task-run -- -n up`
- `python -m py_compile scripts/haac.py scripts/haac_loop.py scripts/hydrate-authelia.py`
- `python -m unittest discover -s tests -p "test_haac.py" -v`
- `kubectl kustomize k8s/platform`
- `python scripts/haac.py task-run -- reconcile:gitops`
- live Litmus API verification that the expected experiments exist
- browser verification that Litmus authenticates and reaches an already-seeded experiment surface

### Recovery and rollback

- rerunning `chaos:post-install` or `reconcile-litmus-chaos` is the supported recovery path for failed or partial experiment seeding
- removing a catalog entry in wave1 does not auto-delete the already-saved Litmus experiment or supporting `ChaosExperiment`; rollback requires manual deletion in Litmus and/or the `litmus` namespace
