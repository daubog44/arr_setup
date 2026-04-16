## Overview

The failure is caused by a deployment mismatch, not by the intended auth matrix. Grafana is configured to read `GRAFANA_OIDC_SECRET` from the environment, but the repo-generated `grafana-oidc-secret` currently exposes the key as `clientSecret`. Because the Grafana chart imports the secret via `envFromSecret`, the container gets `clientSecret=<value>` instead of `GRAFANA_OIDC_SECRET=<value>`, and the token endpoint request goes out without the expected client secret.

## Design

### Secret wiring

- Keep the secret object name `grafana-oidc-secret`.
- Change the rendered secret payload key from `clientSecret` to `GRAFANA_OIDC_SECRET`.
- Do not change the Authelia OIDC client registration; it already expects the same underlying operator input value.

### Browser verification

- Keep Grafana as `native_oidc`.
- Tighten the verification rule in `scripts/verify-public-auth.mjs`:
  - fail fast on `Failed to get token from provider`
  - fail if the browser remains on `/login`
  - only pass when the flow lands on an authenticated Grafana page

### Reconciliation

- Regenerate secrets from source-of-truth operator inputs.
- Reconcile the affected GitOps layer so the monitoring namespace rolls the updated secret wiring.
- Re-run browser verification after the rollout.

## Verification

- `openspec validate fix-grafana-authelia-oidc`
- `helm template haac-stack k8s/charts/haac-stack`
- `python scripts/haac.py verify-web --domain nucleoautogenerativo.it`
- `task reconcile:argocd`
- `node scripts/verify-public-auth.mjs`
