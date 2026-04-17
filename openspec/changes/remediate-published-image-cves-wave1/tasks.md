## 1. Evidence and prioritization

- [ ] 1.1 Capture live Trivy evidence for the highest-CVE published workloads and map each workload to its source-managed image tag
- [ ] 1.2 Classify low-risk upgrade candidates separately from compatibility-sensitive media services

## 2. Remediation

- [ ] 2.1 Upgrade the low-risk published-service images that have upstream fixes available
- [ ] 2.2 Evaluate the highest-CVE media services and either upgrade them safely or document concrete blockers in the change docs

## 3. Verification

- [ ] 3.1 Validate with OpenSpec, tests, render gates, and `task -n up`
- [ ] 3.2 Verify live Trivy deltas and browser-check every touched public service
