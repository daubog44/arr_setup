## Context

The repo already has a cleanup boundary in `scripts/haac.py`, but it only knows about older investigation artifacts. Recent browser verification and local shell/runtime side effects create different top-level clutter that remains untracked noise:

- `.playwright-cli/` captures from Playwright CLI
- `.playwright/` browser state
- root-level path fragments (`Factory/`, `Microsoft/`, `ITS/`, `Talent/`, `Tech/`, `-/`) that are consistent with misquoted absolute workspace paths on Windows

The goal is not to aggressively delete arbitrary files. The goal is to codify the known junk set that is outside the product contract and make cleanup idempotent.

## Goals

- Keep the supported local-artifact boundary under `.tmp/` and `output/`.
- Ensure the built-in cleanup task removes current known junk safely.
- Prevent transient browser artifacts from appearing as untracked repo changes.

## Non-Goals

- Reworking Codex desktop runtime storage.
- Changing the Playwright CLI itself.
- Deleting user-created files that are not part of the known artifact set.

## Design

1. Expand the cleanup artifact list in `scripts/haac.py` to include:
   - `.playwright/`
   - `.playwright-cli/`
   - the root-level broken-path residue directories observed in this repo

2. Extend `.gitignore` so transient Playwright directories and the known broken-path residue roots do not show up as trackable repo content.

3. Keep `task clean-artifacts` as the operator surface; do not add a second cleanup command unless the current one cannot express the new policy.

4. Add focused regression coverage for the cleanup helper so the known junk set remains intentional.

## Risks

- Over-cleaning a legitimate directory with a generic name like `Microsoft/`.
  - Mitigation: restrict the policy to repo-root artifact directories only, matching the evidence seen in this workspace.
- Hiding a real quoting bug by only ignoring the residue.
  - Mitigation: the cleanup policy documents that these are broken-path residues. If a repo-controlled command is later proven to create them, that root cause should be fixed in a separate change.
