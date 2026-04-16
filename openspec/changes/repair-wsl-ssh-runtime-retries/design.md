## Design

### Evidence

The reconcile path failed with repeated messages that `/tmp/haac-runtime/Debian/haac_ed25519` and `/tmp/haac-runtime/Debian/haac_known_hosts` were missing while `ssh_tunnel()` was retrying the Windows/WSL tunnel. The current control flow builds the tunnel command once before the retry loop, but it also calls `cleanup_wsl_runtime()` in the loop cleanup path.

### Solution shape

- Build the tunnel command inside the retry loop instead of once before it.
- Preserve the existing runtime cleanup behavior after each attempt and after successful teardown.
- Add a unit test proving that retries regenerate the tunnel command each time.

### Verification

- `openspec validate repair-wsl-ssh-runtime-retries`
- `PYTHONPATH=scripts python -m unittest discover -s tests -p "test_haac.py" -v`
- `python scripts/haac.py task-run -- -n reconcile:argocd`
