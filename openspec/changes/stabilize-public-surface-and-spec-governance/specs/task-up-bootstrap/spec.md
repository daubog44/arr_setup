## MODIFIED Requirements

### Requirement: Public service URL reporting

The system MUST produce a final public endpoint report for the services exposed through the homelab ingress and Cloudflare path.

#### Scenario: Successful endpoint summary

- **WHEN** bootstrap succeeds
- **THEN** the final output MUST include the list of enabled official UI URLs with service name, namespace, auth expectation, and verification status

#### Scenario: Endpoint source of truth

- **WHEN** the system builds the public endpoint report
- **THEN** it MUST derive URLs from the official public UI catalog rather than maintaining an unrelated duplicated list

### Requirement: Browser-level endpoint verification

The system MUST support browser-level verification of the final public URLs in addition to HTTP-level reachability checks when the operator workflow is being validated through the autonomous loop.

#### Scenario: Public URL verification through the loop

- **WHEN** the autonomous loop validates the final public endpoint report
- **THEN** it MUST navigate the enabled official UI URLs rather than arbitrary wildcard hosts
