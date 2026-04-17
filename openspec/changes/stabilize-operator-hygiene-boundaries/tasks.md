## 1. Publication recovery

- [x] 1.1 Make GitOps publication recover cleanly when the remote branch moves during the publish window
- [x] 1.2 Detect repo-owned untracked-file collisions before `task sync` attempts a fast-forward

## 2. Identity boundary

- [x] 2.1 Remove implicit Grafana/downloader credential coupling and add an explicit downloader shared-credential opt-in
- [x] 2.2 Update `.env.example`, docs, and preflight warnings to explain the supported credential hierarchy

## 3. Workspace hygiene

- [x] 3.1 Narrow automatic cleanup to disposable roots and prune empty sanctioned scratch directories only
- [x] 3.2 Delete the remaining tracked legacy artifact files from Git instead of runtime cleanup

## 4. Verification

- [x] 4.1 Add focused regression coverage for publication race recovery, sync collision guidance, identity defaults, and cleanup
- [x] 4.2 Validate with OpenSpec, local tests, clean-artifacts, dry-run/bootstrap gates, live ArgoCD sync, and browser verification
