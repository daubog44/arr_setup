## Design

The canonical environment remains `haac-default`.

Flow:

1. Log in to Litmus and ensure `haac-default` exists and is healthy.
2. Query the environment list.
3. If the legacy `test` environment exists:
   - mark the environment removed in Mongo
   - mark its stale infra records removed as well
   - restart `litmus-server` so the UI stops surfacing the legacy path

Why direct Mongo:

- the Litmus GraphQL surface used in this repo exposes create/update behavior but not a reliable environment-removal path for the current deployed version
- forcing a second cluster-scope infra for `test` is not the right fix because it leaves two conflicting infra paths in the same cluster

This is a migration, not a second supported environment.
