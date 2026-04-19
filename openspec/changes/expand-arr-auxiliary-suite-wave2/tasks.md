## 1. Auxiliary services

- [ ] 1.1 Add repo-managed Lidarr manifests, ingress/Homepage wiring, storage, and API bootstrap
- [ ] 1.2 Add repo-managed SABnzbd manifests, ingress/Homepage wiring, storage, and API bootstrap

## 2. Cross-service automation

- [ ] 2.1 Extend `media:post-install` so Prowlarr, Lidarr, and SABnzbd are linked through supported API flows
- [ ] 2.2 Extend Seerr/Jellyfin/Homepage docs to describe the supported auxiliary media contract and why deferred apps stay out of this wave

## 3. Observability

- [ ] 3.1 Add Prometheus/Alloy scrape coverage and Grafana visibility for newly supported auxiliary services
- [ ] 3.2 Validate with OpenSpec, focused unit tests, Helm render, live `media:post-install`, and browser verification
