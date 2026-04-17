# headlamp-operator-surface Specification

## ADDED Requirements

### Requirement: Headlamp operator surface avoids fragile worker-only placement

The repo-managed Headlamp deployment MUST render as an operator-surface workload that does not depend on arbitrary worker placement for public availability.

#### Scenario: Headlamp deployment is rendered

- **WHEN** the Helm chart renders the Headlamp deployment
- **THEN** the pod template MUST target the control-plane node role
- **AND** it MUST tolerate the control-plane `NoSchedule` taint so the deployment remains schedulable

### Requirement: Operator-surface probes and verification distinguish route instability

Headlamp and Homepage readiness, plus browser verification for operator surfaces, MUST not treat route-level outages as if the UI merely fell back to internal auth.

#### Scenario: Singleton operator HTTP probes are rendered

- **WHEN** the Helm chart renders singleton operator-surface liveness and readiness probes for Headlamp or Homepage
- **THEN** each probe MUST declare an explicit timeout budget greater than one second

#### Scenario: Public operator route returns a gateway error

- **WHEN** browser verification reaches an authenticated operator route such as `headlamp.<domain>` or `home.<domain>`
- **AND** the rendered page contains a gateway failure such as `502` or `Bad gateway`
- **THEN** verification MUST fail with a gateway-specific error instead of reporting an internal-login fallback or generic content timeout
