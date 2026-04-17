## 1. Kyverno baseline

- [x] 1.1 Add Kyverno as a repo-managed platform application
- [x] 1.2 Add a small high-signal baseline of policies plus explicit exceptions
- [x] 1.3 Add Policy Reporter UI with the Kyverno plugin and publish it through the official UI catalog

## 2. Runtime hardening

- [x] 2.1 Add repo-managed PSA namespace labels with documented carve-outs
- [x] 2.2 Add a curated Falco homelab rule bundle
- [x] 2.3 Add a post-install security phase that reconciles Falco rule assets without bloating the main Taskfile

## 3. Validation

- [x] 3.1 Update stable specs and validate with OpenSpec, Helm, Kustomize, and bootstrap dry-run
