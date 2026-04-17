## ADDED Requirements

### Requirement: Homepage Kubernetes health checks must remain ready behind host validation

The repo-managed Homepage deployment MUST allow kubelet health checks without weakening the public hostname contract for normal traffic.

#### Scenario: Kubelet probes the Homepage pod directly

- **WHEN** Kubernetes executes Homepage readiness or liveness probes against the pod IP
- **THEN** the deployment MUST include the current pod IP in `HOMEPAGE_ALLOWED_HOSTS`
- **AND** the probes MUST target Homepage's dedicated health endpoint rather than the dashboard route

#### Scenario: Public Homepage traffic still uses the managed domain

- **WHEN** Homepage serves public traffic through the configured ingress host
- **THEN** the deployment MUST continue to allow the managed public hostname
- **AND** the public route MUST not depend on kubelet probes using that hostname
