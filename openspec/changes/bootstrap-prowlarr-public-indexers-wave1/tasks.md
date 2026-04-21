## 1. Contracts

- [x] 1.1 Add OpenSpec delta(s) for repo-managed public Prowlarr indexer bootstrap

## 2. Implementation

- [x] 2.1 Add an idempotent Prowlarr indexer bootstrap helper driven by live schema payloads
- [x] 2.2 Seed a minimal public baseline for movies and TV inside media post-install
- [x] 2.3 Verify downstream ARR apps receive synced indexers from Prowlarr

## 3. Validation

- [x] 3.1 Validate with focused tests and repo render gates
- [x] 3.2 Prove a fresh cluster exposes the seeded indexers after `task up`
- [x] 3.3 Prove `verify:arr-flow` passes candidate selection without manual Prowlarr UI setup
