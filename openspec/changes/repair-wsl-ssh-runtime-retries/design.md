## Design

### Evidence

The reconcile path failed with repeated messages that `/tmp/haac-runtime/Debian/haac_ed25519` and `/tmp/haac-runtime/Debian/haac_known_hosts` were missing while `ssh_tunnel()` was retrying the Windows/WSL tunnel. The current control flow builds the tunnel command once before the retry loop, but it also calls `cleanup_wsl_runtime()` in the loop cleanup path.

Additional live evidence on April 17, 2026 showed `cluster_session()` failures even outside the retry path when two Windows-side calls touched the shared WSL runtime in close succession. The shared `/tmp/haac-runtime/Debian` directory let one session remove or rewrite runtime-backed SSH material that another session was still using, which surfaced as `cp ... file exists` and missing-file errors during key staging.

### Solution shape

- Build the tunnel command inside the retry loop instead of once before it.
- Scope the WSL runtime directory to the current process/thread by default so concurrent Windows-side sessions do not share or delete each other's SSH materials.
- Preserve the existing runtime cleanup behavior after each attempt and after successful teardown, but only inside the scoped runtime directory.
- Add unit tests proving that retries regenerate the tunnel command each time and that runtime directories are isolated.

### Verification

- `openspec validate repair-wsl-ssh-runtime-retries`
- `PYTHONPATH=scripts python -m unittest discover -s tests -p "test_haac.py" -v`
- `python scripts/haac.py task-run -- -n reconcile:argocd`
