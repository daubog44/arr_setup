# public-ui-surface Delta

## MODIFIED Requirements

### Requirement: Falco and Litmus are first-class official UIs when enabled

The operator-visible UI catalog MUST include Falco and Litmus when those UIs are intentionally published.

#### Scenario: Falco is enabled

- **WHEN** Falco is enabled in operator inputs
- **THEN** the official route catalog MUST publish the Falcosidekick Web UI through the shared ingress pattern
- **AND** Homepage MUST include the Falco UI link
- **AND** the Falco profile MUST avoid the known unprivileged-LXC legacy-eBPF and persistent-Redis failure modes of this cluster

#### Scenario: Official protected UI uses shared auth

- **WHEN** Falco, Litmus, Semaphore, Homepage, or other official app UIs are published
- **THEN** those routes MUST be protected through the shared Authelia forward-auth chain unless explicitly declared public
