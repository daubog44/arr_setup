## Context

The ArgoCD bootstrap currently applies the upstream install manifest directly from GitHub using `k3s kubectl apply --server-side --force-conflicts`.

That is a reasonable default, but on this cluster the API server can temporarily fail OpenAPI discovery while still being healthy enough to process normal apply requests. In that state, client-side schema validation blocks bootstrap even though the desired manifest is valid.

## Goals / Non-Goals

**Goals**

- remove the bootstrap dependency on temporary OpenAPI discovery success for the ArgoCD install step
- keep the ArgoCD install behavior idempotent
- preserve direct upstream-manifest bootstrap without redesigning the GitOps topology

**Non-Goals**

- vendor the ArgoCD install manifest into the repo
- redesign the Sealed Secrets or ArgoCD bootstrap order
- solve later ArgoCD sync or workload health issues in this change

## Decisions

### Disable client-side validation for the upstream ArgoCD install apply

The failure is specifically in the client's attempt to download and use OpenAPI for validation. The minimal supported fix is to run the same apply with `--validate=false`, while keeping `--server-side` and `--force-conflicts`.

### Keep the change scoped to the ArgoCD install step

Sealed Secrets already rolls out successfully after the networking fix. The new blocker is isolated to ArgoCD bootstrap, so the change should touch only that apply path and its validation evidence.

## Risks / Trade-offs

- Disabling client-side validation reduces one safety check for this bootstrap apply.
  - Acceptable here because the manifest comes from a pinned upstream release URL and server-side admission still runs.
- This does not guarantee full `task up` completion.
  - Acceptable. The change is specifically about moving bootstrap beyond the observed ArgoCD install blocker.
