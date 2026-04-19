## Design

### Scope boundary

This wave adds a supported verifier for one safe end-to-end movie flow. It does not expand the default bootstrap path and it does not try to automate a permanent indexer catalog for every deployment.

The supported outcome is:

1. prove ARR download-client connectivity
2. prove one safe movie can be requested
3. prove one seeded release is queued/downloaded through qBittorrent over the VPN path
4. prove the imported file appears on the NAS-backed media tree
5. prove Jellyfin can see the imported title

### Operator surface

The repo will add one explicit task, separate from `task up`, for example:

- `task verify:arr-flow`

That task will call a new `scripts/haac.py` command and run only when the operator asks for it.

This keeps the bootstrap idempotent and non-surprising while still giving the repo a supported acceptance gate for the media path.

### Candidate strategy

The verifier should use a curated list of safe movie candidates that are practical for homelab validation:

- public-domain or openly licensed
- small enough to finish in a reasonable homelab window
- known to exist in Seerr/TMDb and in the live Prowlarr indexer results with the correct year

The verifier should not blindly hardcode one fragile title. It should:

- search a small preferred list in Seerr
- cross-check the year/title combination against Prowlarr search results
- choose the first candidate that has seeded results
- fail with a concrete message if no candidate is viable

### Download-path proof

The verifier should explicitly test or observe:

- `Radarr` qBittorrent download client test passes
- `Prowlarr` has at least one enabled movie-capable indexer that returns seeded results for the chosen candidate
- `FlareSolverr` is wired when the configured indexer path needs it
- the resulting download appears in qBittorrent
- the imported file lands under the NAS-backed movie root

The verifier should prefer proving the real NAS-backed path over only checking a pod-local PVC.

### Jellyfin proof

Once the import finishes, the verifier should:

- trigger a library refresh if needed
- authenticate with the repo-managed Jellyfin admin identity
- query Jellyfin for the imported title

The accepted outcome is that Jellyfin can query the title by name; browser playback is optional and may be skipped when codec/browser constraints make it noisy.

### Verification

- `openspec validate stabilize-arr-e2e-download-flow-wave5`
- `python scripts/haac.py check-env`
- `python scripts/haac.py doctor`
- `python scripts/haac.py task-run -- -n up`
- `python -m py_compile scripts/haac.py scripts/haac_loop.py scripts/hydrate-authelia.py`
- `python -m unittest discover -s tests -p "test_haac.py" -v`
- `helm template haac-stack k8s/charts/haac-stack`
- `kubectl kustomize k8s/bootstrap/root`
- `kubectl kustomize k8s/platform`
- `kubectl kustomize k8s/workloads`
- `python scripts/haac.py task-run -- media:post-install`
- `python scripts/haac.py task-run -- verify:arr-flow`
- browser/API verification for the resulting Seerr/Jellyfin surfaces when the flow reaches them

### Recovery and rollback

- rerunning `task verify:arr-flow` is the supported recovery path for verifier-only failures
- rerunning `task media:post-install` remains the supported recovery path for media bootstrap drift
- rerunning `task up` remains the full recovery path for cluster-wide drift
- rollback removes only the verifier command/task/docs; it must not tear down the working media stack
