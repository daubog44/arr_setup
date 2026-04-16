## Why

The live GitOps reconcile path on Windows currently fails before the K3s API session is established. When `deploy-argocd` retries the SSH tunnel, the Windows/WSL runtime directory gets cleaned between attempts but the tunnel command keeps reusing the old private key and `known_hosts` paths. That turns a retryable tunnel/authentication failure into a guaranteed stale-path failure on the next attempt.

## What Changes

- Rebuild the Windows/WSL-backed SSH tunnel command on every retry attempt so the runtime-backed key material is recreated after cleanup.
- Add a focused regression test for the retry path.
- Record the retry/runtime contract as a stable repo capability.

## Capabilities

### New Capabilities
- `wsl-tunnel-runtime`: Windows/WSL retryable SSH tunnels recreate their runtime-backed key and `known_hosts` files on every attempt.

## Impact

- Affected code lives in `scripts/haac.py` plus focused regression coverage in `tests/test_haac.py`.
- This change improves the reliability of the official Windows bootstrap path without changing the operator contract.
