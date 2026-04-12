## Why

The committed rerun from `d9dfae13d16d70f9235e084ef5025ad4d1946287` did not reach GitOps publication or the `haac-stack` workload gate again. It stayed in `configure-os` for more than 45 minutes while WSL-side `ansible-playbook` remained stuck in `AnsiballZ_systemd.py` against both workers during `k3s-agent` service management. That violates the operator contract that `task up` is the normal rerun path unless the output explicitly says manual intervention is required.

## What Changes

- Replace unbounded K3s and `k3s-agent` restart paths in `ansible/playbook.yml` with bounded recovery steps that do not wait forever inside the Ansible `systemd` module.
- Make the recovery path capture `systemctl status` plus recent `journalctl -u <service>` output before failing so the operator gets an actionable node-configuration error instead of a silent hang.
- Keep the scope narrow to K3s service recovery during `configure-os`; do not redesign the broader cluster recovery flow in this change.

## Capabilities

### New Capabilities

- `k3s-service-recovery`: bound K3s service restart/reload behavior during node configuration so `task up` either progresses or fails with explicit recovery evidence.

## Impact

- `ansible/playbook.yml`
- `ansible/tasks/` if a reusable helper is introduced
- validation and worklog evidence around bounded `configure-os` recovery
