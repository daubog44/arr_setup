# Security Stack Reference

This guide explains the layered security posture of the repo-managed stack.

## Security Layers

The stack is intentionally layered. No single tool owns every threat.

## Edge And Identity

- Cloudflare
  - public DNS
  - tunnel ingress
  - edge-layer volumetric protection
- Authelia
  - primary web auth layer for protected apps
- app-native auth
  - used where a service keeps its own login model or native OIDC flow

Cloudflare and Authelia are not interchangeable:

- Cloudflare protects and publishes the edge
- Authelia controls authenticated operator access for protected surfaces

## Cluster Policy And Configuration Guardrails

- Kyverno
  - admission-time validation and mutation
  - policy reports surfaced through Policy Reporter
- Sealed Secrets
  - repo-managed encrypted secret publication
- ArgoCD
  - desired-state enforcement and drift visibility

Kyverno prevents unsupported manifests from entering the cluster; it does not replace runtime detection or network-edge inspection.

## Runtime And Posture Detection

- Falco
  - runtime event detection
  - useful for suspicious process, socket, shell, or container behavior
- Trivy Operator
  - image, config, RBAC, and secret/posture scanning
- Prometheus/Grafana/Loki
  - metrics, dashboards, and logs for the operator surface

These tools are mostly detective controls. They tell you something looks wrong; they do not automatically absorb volumetric network floods.

## CrowdSec In This Repo

CrowdSec is the behavior-based remediation layer for the ingress path.

Repo-managed behavior:

- CrowdSec runs in-cluster
- Traefik access logs are acquired by CrowdSec
- the Traefik CrowdSec bouncer middleware is mounted declaratively
- CrowdSec AppSec is enabled for request inspection
- malicious application-layer probes can be blocked before they reach the backend

Observability note:

- LAPI alerts, decisions, and metrics are available from CrowdSec itself
- Traefik plus CrowdSec request blocking is also observable from Traefik access logs and live HTTP probes
- the upstream Traefik bouncer integration does not give a rich first-party dashboard surface on its own, so the repo treats live blocking evidence plus CrowdSec decisions/alerts as the source of truth

The supported proof in this repo is an intentionally bad request such as `/.env` returning `403` through the Traefik plus CrowdSec path.

The repo keeps `crowdsecurity/http-crawl-non_statics` in simulation mode. That scenario is low-confidence and produced false positives against supported SPA-style operator UIs such as Headlamp and Policy Reporter/Kyverno during real browser verification. The signal remains visible, but remediation from that scenario is intentionally disabled.

The repo also keeps a narrow repo-managed false-positive contract for supported operator/media paths that legitimately create noisy `403` or AppSec matches during normal verification:

- Ntfy topic publishing on `/homelab` and `/haac-alerts`
- Jellyfin playback progress on `/Sessions/Playing/Progress`
- a small Grafana auxiliary route set used by the official SPA shell
- legacy operator-browser cleanup for Servarr SignalR negotiate requests and old Grafana datasource-proxy verification traffic

Those paths are allowlisted by exact path plus host conditions only. OWASP CRS and the broader CrowdSec AppSec surface remain enabled for the rest of the ingress.

The repo-managed browser verifier deliberately does not query Prometheus through Grafana's datasource proxy anymore. That browser pattern triggered CrowdSec AppSec `sql_injection` false positives against benign PromQL verification requests. Metric-family proof remains covered by the cluster-local Python verification ladder instead of the public browser path.

## CrowdSec Versus DDoS

CrowdSec helps with intelligent application-layer abuse handling:

- repeated malicious probes
- known-bad HTTP patterns
- WAF-style signatures and virtual patching
- decision-based bans/challenges at the request layer

CrowdSec is not a substitute for edge-scale volumetric DDoS absorption.

Practical boundary:

- Cloudflare is the real protection layer for large volumetric DoS/DDoS at the internet edge
- CrowdSec helps with L7 abuse detection and remediation after traffic reaches the cluster ingress path

If you want "total" DDoS protection, that has to be read honestly:

- in-cluster tools cannot fully replace upstream network capacity and edge scrubbing
- the strongest posture is Cloudflare at the edge plus CrowdSec AppSec/remediation inside the application path

## Tool-To-Question Map

Use this quick map when triaging an issue:

- "Why is this host or route public?"
  - Cloudflare + Traefik + Homepage ingress catalog
- "Who can log in?"
  - Authelia, app-native auth, and `HAAC_MAIN_*`
- "Why was this manifest rejected?"
  - Kyverno / Policy Reporter
- "Why did this pod or process behave suspiciously?"
  - Falco
- "Which image or RBAC/config issue is risky?"
  - Trivy Operator
- "Why did an inbound malicious request get blocked?"
  - CrowdSec + Traefik

## Operator Notes

- CrowdSec secrets and bouncer wiring are repo-managed from templates and `.env`
- Falco signal quality matters more than raw event volume; repo-specific rules should be tuned to reduce known operator-noise
- Trivy findings need triage: some are actionable package updates, others are upstream-image debt that cannot be solved purely in this repo
