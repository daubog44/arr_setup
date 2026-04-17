## Design

### Evidence

- `git rev-parse HEAD` and `origin/main` resolved to `d831d4d26cb2143956dfb3fb682c835fc8e94cc7`.
- Live cluster inspection on April 17, 2026 showed:
  - `argocd/application/haac-root` synced to `05a3b8e13e1abffcfe0977957161ee465ffdaa63`
  - `argocd/application/haac-platform` synced to `7612105f502194c68994b28d0cac1cd23c02fd02`
  - `argocd/application/kube-prometheus-stack` therefore still rendered the old Helm values with `additionalDataSources`, no `kubeApiServer.serviceMonitor.relabelings`, and no `checksum/grafana-observability-surface`
- `wait-for-argocd-sync` still passed because `wait_for_argocd_application_ready()` only checked `status.sync.status == Synced` and `status.health.status == Healthy`.

### Solution shape

The bootstrap path already knows which Git branch is the GitOps source of truth. This wave adds a narrow freshness layer:

- resolve the expected GitOps revision from the configured remote branch
- refresh `haac-root` immediately after applying the root app manifest
- require repo-managed ArgoCD applications to report `status.sync.revision == <expected git sha>` before the readiness gate succeeds
- when a repo-managed app is healthy but stale, request a hard refresh and keep waiting instead of returning success

This stays narrow because it changes neither the public operator command nor the application topology. It only tightens the definition of "GitOps ready" to match the real commit that `push-changes` published.

### Verification

- `openspec validate enforce-argocd-head-revision-gates`
- `PYTHONPATH=scripts python -m unittest discover -s tests -p "test_haac.py" -v`
- `python scripts/haac.py check-env`
- `python scripts/haac.py doctor`
- `python scripts/haac.py task-run -- -n up`
- `task reconcile:argocd`
- browser verification after reconcile, including explicit Playwright CLI navigation
