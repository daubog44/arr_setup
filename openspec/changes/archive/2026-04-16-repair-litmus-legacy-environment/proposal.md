## Why

The canonical Litmus environment is now automated, but some clusters still retain a legacy `test` environment in the UI. That stale environment sends the operator back into the manual "download/apply YAML" flow even though `task up` already bootstraps the supported canonical environment.

## What Changes

- keep `haac-default` as the only supported canonical Litmus environment
- migrate the legacy `test` environment out of the visible UI path by marking it removed in Mongo when the canonical environment is healthy
- keep browser verification strict so the manual infrastructure wizard remains a regression

## Outcome

After bootstrap and reconcile, the operator sees only the canonical Litmus environment path and is no longer sent into the manual YAML apply flow through the legacy `test` environment.
