## Why

The operator surface still has three real hygiene gaps on April 17, 2026:

- `push-changes` stays publish-only, but if `origin/main` moves between the initial fetch and the final push the operator can still be left with an artificial local Git publication commit instead of a clean recovery path.
- The new identity-default layer still leaks one reverse trust-boundary: Grafana falls back to `QUI_PASSWORD`, and there is no explicit opt-in contract for the user request to reuse one username/password across lower-trust downloader apps too.
- `task clean-artifacts` still mixes safe disposable roots with historical broken-path names and can touch tracked repo state; live worktree evidence already includes tracked deletions under `.playwright-cli/` and `Microsoft/...`.

These are operator-visible problems because they affect the normal rerun path of `task up`, the safety of the credential model, and the cleanliness of the working tree.

## What Changes

- Keep Git merge policy in `task sync`, but make publication races recover cleanly instead of leaving a false local divergence.
- Formalize downloader shared credentials as an explicit opt-in on top of the existing main admin identity defaults, and remove the remaining implicit admin/downloader fallback coupling.
- Narrow automatic cleanup to repo-owned disposable roots, prune empty sanctioned scratch directories, and turn the remaining tracked junk into an intentional one-time Git cleanup.

## Capabilities

### Modified Capabilities

- `bootstrap-boundaries`
- `bootstrap-identity-inputs`
- `workspace-artifact-hygiene`

## Impact

- Affected code lives in `scripts/haac.py`, `scripts/haaclib/envdefaults.py`, `scripts/haaclib/gitstate.py`, `scripts/hydrate-authelia.py`, `scripts/verify-public-auth.mjs`, and `tests/test_haac.py`.
- Operator-facing docs and examples change in `.env.example`, `README.md`, and `ARCHITECTURE.md`.
- The repo will intentionally delete the tracked legacy Playwright snapshot files and the stray tracked `Microsoft/.../ModuleAnalysisCache` file as part of the cleanup contract.
