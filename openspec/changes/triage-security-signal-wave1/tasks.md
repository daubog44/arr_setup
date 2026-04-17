## 1. Security signal triage contract

- [ ] 1.1 Add OpenSpec deltas that classify urgent versus expected Trivy, Kyverno, and Falco findings

## 2. Fix real baseline failures

- [ ] 2.1 Patch repo-managed Argo CD, Falco, Trivy, and Litmus workloads so `require-pod-requests-limits` stops failing in `argocd`, `security`, and `chaos`
- [ ] 2.2 Keep the resource shapes conservative and deterministic for the single-master homelab profile

## 3. Reduce alert noise without hiding real signal

- [ ] 3.1 Narrow the custom Falco socket-tool rule so loopback-only localhost probes do not flood the UI
- [ ] 3.2 Make Trivy policy-style metrics record failed checks only while preserving vulnerability visibility

## 4. Verification

- [ ] 4.1 Add focused regression coverage where imperative bootstrap logic changed
- [ ] 4.2 Validate with OpenSpec, tests, render gates, live GitOps reconciliation, cluster-side security evidence, and browser verification
