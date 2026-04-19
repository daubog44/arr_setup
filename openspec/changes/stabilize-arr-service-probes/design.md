## Context

The repo already treats `media:post-install` as the supported post-install surface for the ARR stack. After the downloader bootstrap fix, the next live failure is narrow and reproducible: the service probes for Radarr, Sonarr, and Prowlarr still expect a legacy `pong` body even though the deployed versions now expose a small JSON payload with `status: OK`.

This is a contract mismatch, not an application outage. The HTTP status is `200`, the apps are reachable through the in-cluster services, and the returned body is structurally healthy.

## Goals / Non-Goals

**Goals:**
- Accept the real healthy `/ping` response of the deployed ARR apps.
- Keep the probe contract explicit and test-covered.
- Move `media:post-install` to the next real blocker instead of failing on stale health expectations.

**Non-Goals:**
- This wave does not automate TRaSH/Recyclarr profiles yet.
- This wave does not add new ARR applications.
- This wave does not redesign the broader post-install sequence.

## Decisions

### 1. Match on semantic health, not one legacy literal

The probe should accept the actual success shape returned by the deployed versions. The simplest stable contract is to keep HTTP `200` mandatory and match the success body on `OK` instead of the older `pong` literal.

Rejected alternative:
- Drop body validation entirely. That would lose a useful guardrail against HTML error pages or misrouted ingress responses on port-forwarded service probes.

### 2. Keep the change narrow

The next safe step is only to repair the service-probe contract so the media bootstrap can progress to the later ARR setup work. TRaSH profiles, Seerr automation, and extra apps will each need their own evidence-backed waves once the current operator path is truthful.

## Risks / Trade-offs

- [Risk] A future ARR image could change the probe body again. -> Mitigation: add regression coverage around the accepted success pattern and keep the matching semantic (`OK`) rather than overfitting to full JSON formatting.
- [Risk] Matching `OK` could be too permissive if an unrelated page includes that string. -> Mitigation: retain the HTTP `200` requirement and keep these checks on direct service port-forwards, not public routes.
