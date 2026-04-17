## ADDED Requirements

### Requirement: Litmus MongoDB replica-set credentials are repo-managed and stable

The Litmus MongoDB subchart MUST consume a repo-managed existing Secret for its root password and replica-set key so chart renders remain deterministic.

#### Scenario: Rendering Litmus twice does not rotate the replica-set key

- **WHEN** the Litmus chart is rendered multiple times from the same `.env`
- **THEN** the MongoDB credentials consumed by Litmus stay stable
- **AND** the chart does not generate a new random `mongodb-replica-set-key`

### Requirement: Litmus homelab MongoDB topology stays single-node

The Litmus MongoDB deployment for this homelab MUST not depend on an arbiter pod when only one data-bearing replica is configured.

#### Scenario: Litmus renders a single-node replica set without an arbiter

- **WHEN** the Litmus chart is rendered from the repo-managed values
- **THEN** `mongodb.replicaCount` remains `1`
- **AND** `mongodb.arbiter.enabled` is `false`
- **AND** Litmus uses a single `litmus-mongodb-0.litmus-mongodb-headless` DB endpoint

### Requirement: Litmus bootstrap survives normal pod restarts

The Litmus MongoDB replica set MUST remain internally authenticated after normal restarts of the primary, arbiter, and portal deployments.

#### Scenario: Litmus backend recovers after MongoDB and portal restarts

- **WHEN** the pinned MongoDB secret is reconciled and Litmus workloads restart
- **AND** the previous arbiter-backed MongoDB data is reset once during migration
- **THEN** `litmus-mongodb-0` becomes Ready
- **AND** `litmus-auth-server` and `litmus-server` reach Available
- **AND** the Litmus post-install reconcile path can proceed without manual secret repair
