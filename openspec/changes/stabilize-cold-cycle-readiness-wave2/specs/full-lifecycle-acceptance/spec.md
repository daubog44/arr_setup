## MODIFIED Requirements

### Requirement: Cold-cycle acceptance must survive residual bootstrap drift without manual cleanup

The repo-managed `down -> up -> verify` acceptance path MUST tolerate the currently proven residual drift surfaces that appear only after a destructive lifecycle.

#### Scenario: Included Taskfiles use the same cold-cycle-safe master IP resolver

- **WHEN** the operator runs repo-supported follow-up tasks such as `security:post-install`, `media:post-install`, or `chaos:post-install` after a cold cycle
- **THEN** each included Taskfile MUST resolve `MASTER_IP` through the repo-managed `scripts/haac.py master-ip` helper instead of an inline loopback fallback

#### Scenario: CrowdSec stale machine rows do not stall staged readiness

- **WHEN** persisted CrowdSec LAPI data contains stale `agent` or `appsec` machine registrations from a previous cluster incarnation
- **THEN** the staged readiness path MUST be able to prune only the stale runtime registrations that block the recreated pods
- **AND** the `crowdsec` ArgoCD application MUST be able to converge to `Healthy` without manual `cscli` cleanup

#### Scenario: Grafana browser verification fails only on real dashboard health errors

- **WHEN** the browser verifier opens the repo-managed Kubernetes API server dashboard in Grafana
- **THEN** it MUST fail on datasource, query, render, or `No data` errors
- **AND** it MUST NOT fail solely because one unstable panel label is absent while the dashboard shell otherwise loads correctly
