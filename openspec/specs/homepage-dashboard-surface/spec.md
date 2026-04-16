# homepage-dashboard-surface Specification

## Purpose
Define the repo-managed Homepage card contract so official service entries, widgets, and icons render as a usable operator dashboard instead of a plain link list with broken assets.

## Requirements
### Requirement: Homepage cards render the repo-managed dashboard surface

Homepage MUST render the card metadata declared in the repo-managed ingress catalog instead of collapsing it to plain links only.

#### Scenario: Homepage services config is rendered

- **WHEN** the chart renders Homepage `services.yaml`
- **THEN** each enabled official card MUST carry its repo-managed `href`, `description`, and supported icon value
- **AND** cards with declared `homepage_widget` metadata MUST render that widget block into the final Homepage config
- **AND** cards with route-local monitoring metadata MUST render a usable `siteMonitor` entry

### Requirement: Homepage widget credentials stay secret-backed

Homepage MUST consume widget credentials through repo-managed secret interpolation rather than embedding raw secrets into the config map.

#### Scenario: Secret-backed widget is rendered

- **WHEN** a Homepage card declares widget credentials
- **THEN** the final rendered service entry MUST reference `HOMEPAGE_VAR_*` placeholders
- **AND** the Homepage deployment MUST load those values through a repo-managed secret
