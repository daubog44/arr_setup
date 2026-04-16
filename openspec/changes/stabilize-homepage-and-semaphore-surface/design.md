## Design

### Homepage surface

The ingress catalog already carries `homepage_widget`, icon, and route metadata, and the repo already generates a dedicated `homepage-widgets-secret`. The missing piece is template rendering:

- emit `widget:` and `siteMonitor:` blocks into `services.yaml`
- switch broken cards to supported icon sources (`mdi-*` or `si-*`) instead of missing image filenames
- keep widget secrets injected through `envFrom` so service credentials stay out of the config map

### Semaphore bootstrap

The current template is too large and hides behavior inside a long inline shell block. This wave moves that logic into a chart-owned script file mounted via config map so post-install behavior stays modular and diffable.

The same extraction wave fixes the schedule payload shape:

- use `active: true` instead of the currently ineffective `enabled: true`
- give schedules stable human-readable names
- add checksum annotations so Argo can recreate the Job when the script changes

### Verification

- `openspec validate stabilize-homepage-and-semaphore-surface`
- `& .\.tools\windows-amd64\bin\helm.exe template haac-stack k8s\charts\haac-stack`
- `python scripts/haac.py task-run -- -n up`
- live Semaphore API inspection for schedule `active` state when cluster access is available
