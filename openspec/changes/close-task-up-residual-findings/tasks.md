## 1. Implementation

- [x] 1.1 Make Falco platform rendering capability-gated for this unprivileged LXC stack and keep the enabled path documented around the `ebpf` driver
- [x] 1.2 Confirm the supported Proxmox provider object names are already in `tofu/main.tf` and remove stale rename work from this change
- [x] 1.3 Regenerate and preserve the rendered GitOps output affected by the Falco template change

## 2. Validation

- [x] 2.1 Validate with `helm template haac-stack k8s/charts/haac-stack`, `openspec validate close-task-up-residual-findings`, and `python scripts/haac.py task-run -- -n up`
- [x] 2.2 Verify Falco no longer degrades the default platform path by rendering a no-op application when `HAAC_ENABLE_FALCO=false` and keeping cluster-side cleanup in `scripts/haac.py`
- [x] 2.3 Rerun `task plan` and confirm the OpenTofu path no longer prints deprecated Proxmox provider warnings
