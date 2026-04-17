## Design

### Evidence

- The current publication path fetches once, commits generated outputs, then pushes directly. If `origin/<revision>` moves in that window the operator gets a generic push failure and can be left with a local publication commit that did not actually publish.
- The current identity implementation still lets Grafana and Homepage widget Grafana auth fall back to `QUI_PASSWORD`, which contradicts the documented separation between control-plane/admin auth and downloader-local auth.
- The current cleanup contract still includes generic root-name directories and a tracked file path in the automatic removal list. The live worktree already shows tracked deletions under `.playwright-cli/` and `Microsoft/Windows/PowerShell/ModuleAnalysisCache`.

### Solution shape

- Recheck the remote revision immediately before publication commit and classify push-time races explicitly. If the remote moved after the publication commit is created, unwind only that auto-generated commit back into local changes and guide the operator to `task sync`, keeping merge policy out of `push-changes`.
- Add an explicit downloader shared-credential flag so one main username/password can cover qBittorrent/QUI only when the operator opts in. Keep the default boundary: `HAAC_MAIN_*` seeds admin/control-plane surfaces only.
- Remove the remaining Grafana-to-downloader fallback. Grafana must use its own effective admin password derived from the admin layer, not downloader auth.
- Reduce cleanup to dedicated disposable roots plus temporary log patterns. Add safe pruning for empty directories under `.tmp/`, and move the remaining tracked junk into an intentional Git cleanup instead of runtime cleanup logic.

### Verification

- `openspec validate stabilize-operator-hygiene-boundaries`
- `python -m py_compile scripts/haac.py scripts/hydrate-authelia.py scripts/haaclib/envdefaults.py`
- `PYTHONPATH=scripts python -m unittest discover -s tests -p "test_haac.py" -v`
- `python scripts/haac.py clean-artifacts`
- `python scripts/haac.py task-run -- -n up`
- `python scripts/haac.py task-run -- wait-for-argocd-sync`
- `node --check scripts/verify-public-auth.mjs`
- `node scripts/verify-public-auth.mjs`
- `powershell -ExecutionPolicy Bypass -File .\haac.ps1 up`
