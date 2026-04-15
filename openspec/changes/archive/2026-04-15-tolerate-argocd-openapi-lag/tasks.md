## 1. Implementation

- [x] 1.1 Update the ArgoCD bootstrap apply command to tolerate temporary OpenAPI discovery lag without dropping server-side apply semantics

## 2. Validation

- [ ] 2.1 Validate with `ansible-playbook --syntax-check`, `openspec validate tolerate-argocd-openapi-lag`, and `python scripts/haac.py task-run -- -n up`
- [ ] 2.2 Rerun `configure-os` live and record whether bootstrap progresses beyond the ArgoCD install step
