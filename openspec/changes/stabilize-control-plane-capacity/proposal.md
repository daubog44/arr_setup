## Why

The K3s master container is currently sized with a hardcoded `4096` MiB memory value in Terraform, while the live control plane is saturating memory and timing out. Verification on April 17, 2026 showed the master with about 15 MiB free RAM, load averages above 100, repeated `http: Handler timeout`, `Slow SQL` against kine/SQLite, `PLEG is not healthy`, and node lease update failures. Those failures line up with the public 502s, readiness probe timeouts, and flaky ArgoCD propagation seen during this loop.

This also violates the repo invariant that infra inputs should come from the central `.env` contract rather than hiding as Terraform literals.

## What Changes

- Add a `.env`-driven input for K3s master memory.
- Replace the hardcoded Terraform master memory value with the new variable.
- Document the input in `.env.example`.
- Apply the higher memory limit live to the current Proxmox master container so the running cluster can recover.
- Refresh repo-managed SSH trust for recreated K3s nodes before the Ansible phase so `task up` stays rerunnable after the master container is replaced.
- Refresh package metadata on freshly recreated K3s nodes before the first baseline package install so `configure-os` does not stop on stale Debian package indexes after the master is replaced.
- Reset and rejoin workers whose persisted K3s agent token/CA trust still points at the old control plane after the master container is replaced.

## Impact

- The control plane gets enough headroom to stop thrashing under the current homelab workload.
- Operators can tune master capacity from `.env` without editing Terraform source.
