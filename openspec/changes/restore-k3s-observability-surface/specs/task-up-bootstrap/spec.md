## MODIFIED Requirements

### Requirement: Final public URL summary includes usable official UIs

Bootstrap success MUST mean the official URLs are not only reachable but usable according to their declared contract.

#### Scenario: Final public URL verification includes Grafana usability

- **WHEN** `task up` reaches the final official URL verification phase
- **THEN** Grafana MUST pass both browser-auth verification and the repo-managed observability usability gate for the shipped official dashboards
