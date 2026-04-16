# Design

## Scope

This change is local-operator hygiene only. It does not alter cluster auth, ArgoCD topology, or Cloudflare publication.

Touched surfaces:

- Windows to WSL Ansible bridge
- repo-local runtime artifact placement
- operator docs and repo cleanup

## WSL Runtime Model

The WSL bridge keeps the bootstrap key repo-local on Windows and creates a runtime-only WSL copy under:

- `.tmp/wsl-runtime/<distro>/`

The flow is:

1. create the runtime directory under `.tmp/`
2. copy the bootstrap key and `known_hosts` into that runtime path
3. run Ansible through `bash -se` with the runtime paths exported
4. sync `known_hosts` back to the repo-managed file
5. delete the runtime directory on exit

This preserves pragmatic SSH trust while removing the persistent WSL home copy.

## Artifact Hygiene

The repo root should not keep ad hoc investigation outputs. Existing stray artifacts are treated as cleanup debt and removed.

Future operator-created scratch artifacts must live under `.tmp/`, including:

- browser captures
- rendered debug manifests
- temporary chart extracts
- local run logs
- WSL runtime files

## Verification

- `python -m py_compile scripts/haac.py`
- `openspec validate ephemeral-wsl-ssh-and-artifact-hygiene`
- `python scripts/haac.py doctor`
- `python scripts/haac.py task-run -- -n up`

When the reachable environment is available, the broader `task up` verification can cover the changed WSL path transitively.
