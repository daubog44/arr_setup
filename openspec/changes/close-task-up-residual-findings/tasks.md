## 1. Implementation

- [ ] 1.1 Make Falco platform rendering capability-gated for this unprivileged LXC stack and keep the enabled path documented around the `ebpf` driver
- [ ] 1.2 Replace the deprecated Proxmox provider object names in `tofu/main.tf`
- [ ] 1.3 Regenerate any rendered GitOps output affected by the Falco template change

## 2. Validation

- [ ] 2.1 Validate with `helm template haac-stack k8s/charts/haac-stack`, `openspec validate close-task-up-residual-findings`, and `python scripts/haac.py task-run -- -n up`
- [ ] 2.2 Publish the GitOps changes and verify Falco no longer degrades platform health: either healthy when enabled or cleanly absent when disabled
- [ ] 2.3 Rerun `task up` and confirm it succeeds without deprecated Proxmox provider warnings
