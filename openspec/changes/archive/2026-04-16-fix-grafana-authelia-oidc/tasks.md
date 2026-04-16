## 1. Secret Wiring

- [x] 1.1 Update the Grafana OIDC secret generation so the secret key name matches the environment variable Grafana reads.
- [x] 1.2 Regenerate the rendered Grafana OIDC Sealed Secret artifact from the source template and `.env`.

## 2. Verification Hardening

- [x] 2.1 Tighten the browser verification contract for Grafana native OIDC so login-page OAuth errors fail the check.
- [x] 2.2 Validate the change with OpenSpec, render checks, GitOps reconcile, and a live browser-auth run.
