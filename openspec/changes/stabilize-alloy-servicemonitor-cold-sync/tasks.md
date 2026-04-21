## 1. Implementation

- [ ] 1.1 Make the Alloy ArgoCD application tolerate missing `ServiceMonitor` CRDs during cold bootstrap

## 2. Validation

- [ ] 2.1 Validate the platform render after the change
- [ ] 2.2 Re-run the cold-cycle `down` then `up` wrapper acceptance path and confirm the `alloy` gate no longer stalls
