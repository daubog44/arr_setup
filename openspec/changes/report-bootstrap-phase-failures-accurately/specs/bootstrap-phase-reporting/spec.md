## ADDED Requirements

### Requirement: Nested `task up` failures report the true bootstrap phase

When `task up` fails inside a nested included task, the streamed recovery summary MUST report the actual bootstrap phase reached by that nested task rather than falling back to an earlier top-level phase.

#### Scenario: GitOps post-install failure stays in GitOps readiness

- **WHEN** `task up` reaches `security:post-install` or `chaos:post-install` and one of those tasks fails
- **THEN** the emitted recovery summary reports `Failing phase: GitOps readiness`
- **AND** the reported `Last verified phase` remains the latest strictly earlier bootstrap phase rather than regressing to `Preflight`

### Requirement: Explicit lower-level recovery summaries are preserved

If a lower-level helper already emits `[recovery]` lines into the streamed output, the wrapper MUST preserve that exact summary instead of re-inferring a different phase.

#### Scenario: Existing summary wins over generic inference

- **WHEN** the streamed output already contains `[recovery] Failing phase`, `[recovery] Last verified phase`, and `[recovery] Full rerun guidance`
- **THEN** the wrapper re-emits that same summary
- **AND** it does not compute a different fallback phase from task-name inference
