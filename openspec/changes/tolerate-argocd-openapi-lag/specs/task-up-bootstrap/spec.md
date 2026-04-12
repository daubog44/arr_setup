## MODIFIED Requirements

### Requirement: bootstrap install of ArgoCD tolerates temporary API validation lag

The `configure-os` bootstrap path MUST not fail solely because the Kubernetes API server is temporarily unable to serve OpenAPI schema data during the upstream ArgoCD install apply.

#### Scenario: ArgoCD install runs while OpenAPI discovery is temporarily unavailable

- **WHEN** bootstrap applies the pinned upstream ArgoCD install manifest
- **AND** the API server would otherwise fail client-side schema validation because OpenAPI discovery is temporarily unavailable
- **THEN** the playbook applies the manifest without client-side validation
- **AND** server-side apply semantics remain enabled
