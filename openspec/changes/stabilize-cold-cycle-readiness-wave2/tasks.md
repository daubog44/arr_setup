## 1. Contracts

- [x] 1.1 Add OpenSpec deltas for cold-cycle readiness residual recovery

## 2. Implementation

- [x] 2.1 Propagate the cold-cycle-safe `master-ip` resolver to the included Taskfiles
- [x] 2.2 Make CrowdSec Kubernetes registration resilient to persisted stale machine rows after a destructive cycle
- [x] 2.3 Keep Grafana browser verification strict on real errors while removing brittle Kubernetes API server panel-text assertions
- [x] 2.4 Add or update focused tests for the new Taskfile, CrowdSec, and verifier contracts

## 3. Validation

- [x] 3.1 Validate with OpenSpec, targeted tests, and render gates
- [x] 3.2 Prove staged ArgoCD readiness and browser verification succeed live without manual CrowdSec cleanup
- [x] 3.3 Close the real `task down -> task up -> verify` acceptance cycle
