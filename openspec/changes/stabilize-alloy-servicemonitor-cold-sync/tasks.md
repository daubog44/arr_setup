## 1. Implementation

- [x] 1.1 Make monitoring-CRD consumer applications tolerate missing `ServiceMonitor`/`PodMonitor` CRDs during cold bootstrap
- [x] 1.2 Improve the child application ordering so `kube-prometheus-stack` lands before monitoring-CRD consumers

## 2. Validation

- [x] 2.1 Validate the platform render after the change
- [x] 2.2 Re-run the cold-cycle `down` then `up` wrapper acceptance path and confirm the `alloy` gate no longer stalls
