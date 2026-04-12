## Context

The current bootstrap path assumes `MASTER_TARGET_NODE` can serve both as the Proxmox node name used by OpenTofu resources and as the workstation-reachable host used for Proxmox API, SSH, and tunnel operations. That assumption broke the live Windows acceptance run because the configured node name `pve` is valid as a Proxmox node identifier but is not resolvable from the workstation. The gap touches cross-cutting bootstrap surfaces: `.env` inputs, preflight checks, OpenTofu provider configuration, Task variable plumbing, and Python helpers that open tunnels or run Proxmox-side commands.

## Goals / Non-Goals

**Goals:**
- Preserve `MASTER_TARGET_NODE` as the Proxmox node identity used inside OpenTofu resources and inventory generation.
- Add one explicit source-of-truth input for the workstation-reachable Proxmox access address used by API, SSH, and tunnel operations.
- Keep backward compatibility for environments where the node name itself is already resolvable by falling back to `MASTER_TARGET_NODE` when the new input is unset.
- Make operator guidance explicit enough that preflight failures point to the correct `.env` field instead of implying local DNS hacks are the only answer.

**Non-Goals:**
- This change does not redesign multi-node Proxmox clusters or per-node address overrides for worker placement.
- This change does not attempt to auto-discover the correct Proxmox address from the local network.
- This change does not replace the current Proxmox authentication model.

## Decisions

### Add `PROXMOX_ACCESS_HOST` as a separate `.env` input

`PROXMOX_ACCESS_HOST` will be the single operator-facing input for the workstation-reachable Proxmox address. It may be an IP or resolvable hostname. `MASTER_TARGET_NODE` remains the Proxmox node name used by OpenTofu resources and generated inventory.

Alternative considered: reusing `MASTER_TARGET_NODE` but requiring operators to set it to an IP/FQDN. Rejected because OpenTofu resources also use that value as `node_name`, and Proxmox node names are not interchangeable with API endpoint hosts.

### Centralize access-host resolution in `scripts/haac.py`

The Python orchestration layer will expose one helper that returns the effective access host, using `PROXMOX_ACCESS_HOST` first and falling back to `MASTER_TARGET_NODE`. Preflight, SSH helpers, tunnel helpers, and Terraform environment mapping will all use that helper.

Alternative considered: updating only `check-env`. Rejected because OpenTofu, SSH tunnels, maintenance helpers, and later bootstrap phases would still use the wrong host.

### Pass the access host explicitly into OpenTofu

OpenTofu will get a dedicated variable for the Proxmox access host, and the provider `endpoint` plus provider-level SSH configuration will use it. Resource `node_name` fields stay bound to `master_target_node` and worker `target_node` values.

Alternative considered: building the provider endpoint directly from environment variables outside Terraform. Rejected because the repo already treats `.env` as the source of truth and maps it centrally into `TF_VAR_*`.

## Risks / Trade-offs

- [Operators may leave `PROXMOX_ACCESS_HOST` unset in environments where the node name is not resolvable] -> Keep the fallback for backward compatibility but update `.env.example`, docs, and failure messages to steer operators to the new field immediately.
- [The change touches both Python and Terraform bootstrap surfaces] -> Validate with OpenSpec, Task dry-run, Python compile checks, and focused preflight/default-gateway helper checks before trying live runs.
- [Existing environments may rely on implicit `MASTER_TARGET_NODE` behavior] -> Preserve fallback semantics so currently working setups do not require immediate `.env` changes.

## Migration Plan

1. Add `PROXMOX_ACCESS_HOST` to `.env.example` and the bootstrap docs.
2. Introduce a central access-host helper and switch preflight, SSH, and tunnel helpers to use it.
3. Add a dedicated Terraform variable and wire the Proxmox provider endpoint/SSH config to it.
4. Validate the bootstrap locally.
5. Re-run the live acceptance path when the real workstation environment provides a reachable Proxmox access host.

## Open Questions

- None for the implementation itself. The remaining unknown is the real Proxmox access value for the current operator workstation, which is environment-specific and outside repo source control.
