## Design

### Scope boundary

This wave adds Whisparr as an ARR-adjacent workload. It does not change Seerr's upstream support boundary and it does not mix adult-media storage into the existing movie root folder.

### Storage and downloader model

Whisparr should follow the same homelab path contract as the existing stack:

- shared container path `/data`
- dedicated root folder under `/data/media/adult`
- dedicated qBittorrent category and imported category
- optional SABnzbd category for parity with the rest of the stack

This keeps hardlinks and instant moves possible on the shared NAS-backed tree while avoiding collisions with the movie library.

### Integration model

The bootstrap should:

1. deploy the Whisparr workload and persistent config
2. create a published route and Homepage card
3. wire Prowlarr to Whisparr through the supported `Applications` API
4. wire qBittorrent and SABnzbd into Whisparr with dedicated categories
5. reconcile the supported root folder and basic media-management settings

Seerr is explicitly out of scope. The docs must say that Whisparr is a standalone ARR-like surface, not something Seerr can request into.

### Observability

If the supported exporter surface does not cover Whisparr, the repo should prefer an explicit limitation over a fake dashboard. If a supported metrics path exists, it should be added to the same Grafana and Prometheus surface used for the rest of the media stack.

### Verification

- `openspec validate expand-whisparr-stack-wave1`
- `helm template haac-stack k8s/charts/haac-stack`
- targeted Python tests for category, application, and route wiring
- `python scripts/haac.py task-run -- media:post-install`
- browser reachability verification for the Whisparr route when the cluster is available

### Recovery and rollback

- `task media:post-install` remains the supported rerun path
- rollback removes the Whisparr route and workload without disturbing the existing movie, TV, and music surfaces
