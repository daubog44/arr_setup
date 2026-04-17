## Summary

This wave turns K3s master memory into an operator input and raises the current master container to a safer baseline.

## Design

Add `LXC_MASTER_MEMORY` to the central `.env` -> `TF_VAR_*` mapping in `scripts/haac.py`, define `variable "lxc_master_memory"` in Terraform, and use that variable in `tofu/main.tf` for the master module instead of the hardcoded `4096`.

For the current environment, set the local `.env` to `LXC_MASTER_MEMORY=6144`. That value fits the observed Proxmox host headroom while still materially relieving the master, which is currently pinned at 4 GiB with almost no free memory.

After the repo contract is updated, apply the same limit live with Proxmox so the cluster does not have to wait for a future full reprovision to benefit.

Because the current Proxmox provider replaces the master container when the memory value changes, the node SSH host key also changes. The bootstrap path currently copies the stale `known_hosts` file into the Windows/WSL Ansible runtime and then fails in `configure-os` with `REMOTE HOST IDENTIFICATION HAS CHANGED!`. This wave therefore also refreshes the repo-managed known-host entries for the K3s master and workers from the Proxmox vantage point immediately before Ansible runs.

The same replacement path also creates a fresh Debian guest whose first package operation can see a stale or missing package index. Live evidence on April 17, 2026 showed `Ensure sudo is installed on K3s nodes for maintenance delegation` failing on the recreated master with `404 Not Found` for `sudo_1.9.16p2-3_amd64.deb` before K3s installation even began. This wave therefore also refreshes apt metadata before that first baseline package install so capacity-driven master replacement does not strand `configure-os` at OS bootstrap.

The replacement also invalidates the old cluster CA hash embedded in the worker agent token. Live evidence on April 17, 2026 showed both workers still carrying `K3S_TOKEN='K10135f6...` in `/etc/systemd/system/k3s-agent.service.env` while the recreated master exported `K10d674...`, and the workers looped on:

- `token CA hash does not match the Cluster CA certificate hash`
- `tls: failed to verify certificate: x509: certificate signed by unknown authority`

This wave therefore also compares the persisted worker agent token to the freshly read master token during worker bootstrap. When they differ, the playbook reuses the existing stale-registration reset path before reinstalling the worker agent so replacement-driven control-plane trust drift does not leave workers stranded outside the rebuilt cluster.

## Verification

- `openspec validate stabilize-control-plane-capacity`
- `python scripts/haac.py task-run -- -n up`
- `PYTHONPATH=scripts python -m unittest discover -s tests -p "test_haac.py" -v`
- Proxmox shows the updated memory limit for CT `100`
- `free -h` inside the master reflects the larger memory limit
- K3s health and public edge routes improve after the bump
- `task up` no longer stops in `configure-os` because of a stale host key for the recreated master
- `task up` no longer stops in `configure-os` on the recreated master because the first apt package install is using a stale package index
- `task up` no longer leaves workers pinned to the old control-plane CA/token after the master is recreated

## Risks

- Raising the master memory limit without checking Proxmox headroom could starve the host; this wave uses the observed host margin first.
- Capacity helps immediately, but future growth may still require moving more workloads off the control plane.
- Recreated nodes pay one apt metadata refresh during baseline bootstrap.
- Worker reset/rejoin after master replacement is disruptive once, but safer than letting agents loop indefinitely against a dead CA.
