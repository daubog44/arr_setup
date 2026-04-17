## 1. Widget wiring

- [ ] 1.1 Rewire the Grafana Homepage widget to a live-compatible protocol/auth surface
- [ ] 1.2 Fix qBittorrent bootstrap readiness and declarative password seeding so the secret-backed API password actually reconciles
- [ ] 1.3 Add secret-driven rollout checks for Homepage and downloaders widget credentials
- [ ] 1.4 Tighten Homepage browser verification so widget API failures break the operator path

## 2. Validation

- [ ] 2.1 Validate with OpenSpec, rendered manifests, dry-run bootstrap, live reconcile, and Playwright browser checks
