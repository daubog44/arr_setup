## 1. Foundation

- [x] 1.1 Add the Go module and Cobra CLI scaffold that can become the long-term operator entrypoint
- [x] 1.2 Preserve the current wrapper contracts while introducing a staged migration seam between wrappers, Taskfile, and implementation code

## 2. Modularization

- [x] 2.1 Extract one or more internal post-install or maintenance paths out of the main Taskfile into subordinate internal task files or equivalent file-backed orchestration
- [x] 2.2 Continue moving focused responsibilities out of the Python monolith into well-scoped modules during the migration
- [x] 2.3 Update the stable bootstrap-boundaries spec to record the internal task boundary

## 3. Validation

- [x] 3.1 Validate with OpenSpec, dry-run bootstrap, and CLI smoke tests
