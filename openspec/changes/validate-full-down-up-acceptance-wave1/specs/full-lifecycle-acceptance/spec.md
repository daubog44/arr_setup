## ADDED Requirements

### Requirement: Cold-cycle lifecycle acceptance is explicit

The repo MUST treat a full `down -> up -> verify` cycle as a supported acceptance surface for the homelab bootstrap.

#### Scenario: The operator validates a destructive lifecycle rerun

- **WHEN** the operator intentionally runs a full cold-cycle acceptance round
- **THEN** the repo MUST support `task down` followed by `task up`
- **AND** the post-bootstrap verification MUST include ArgoCD health, public route verification, and media-path verification

