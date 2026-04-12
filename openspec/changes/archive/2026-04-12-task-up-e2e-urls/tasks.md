## 1. Bootstrap Contract

- [x] 1.1 Document the exact `task up` phase order and expected inputs from `.env`
- [x] 1.2 Define explicit success and failure boundaries for preflight, provisioning, GitOps bootstrap, and endpoint verification
- [x] 1.3 Align wrapper commands and docs so `task up`, `.\haac.ps1 up`, and `sh ./haac.sh up` share one operator contract

## 2. Preflight And Readiness

- [x] 2.1 Define the minimum active checks `doctor` must perform before provisioning starts
- [x] 2.2 Define staged readiness gates for ArgoCD root, platform, workloads, Cloudflare publication, and endpoint verification
- [x] 2.3 Identify which failures should stop the pipeline immediately versus which can be retried

## 3. URL Output Contract

- [x] 3.1 Define the source of truth for public service URLs and auth expectations
- [x] 3.2 Define the final output format for service name, namespace, auth mode, HTTP status, and URL
- [x] 3.3 Define how `verify-all` reports partial versus full success when some endpoints are not reachable

## 4. Validation

- [x] 4.1 Validate the change structure with `openspec validate task-up-e2e-urls`
- [x] 4.2 Validate supporting repo commands such as `task -n up`, Helm render, and Kustomize render
- [x] 4.3 Record the real-environment follow-up needed for a full `task up` run
