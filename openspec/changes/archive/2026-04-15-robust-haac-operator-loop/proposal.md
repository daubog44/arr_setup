# Why

`task up` is now convergent again, but the repo still carries medium-risk robustness debt:

- some bootstrap and GitOps responsibilities are still mixed in one large runner
- the public UI/auth contract is correct in behavior but not yet fully governed as one long-lived hardening stream
- the autonomous loop needs one explicit umbrella change to keep iterating on real gaps instead of reopening bootstrap drift ad hoc

## What Changes

- define one repo-level robustness change for the remaining HaaC hardening work
- tighten the source-of-truth boundary between `.env`, rendered GitOps outputs, and runtime publication
- keep every official UI behind the shared Authelia edge-auth contract unless explicitly public
- continue splitting orchestration logic out of `scripts/haac.py`
- require the loop to keep iterating on real, evidence-backed gaps until no actionable work remains in scope

## Expected Outcome

- the repo has one active umbrella change for remaining robustness work instead of scattered bootstrap follow-ups
- `task up` stays the supported recovery path while the implementation becomes easier to reason about
- official UI routes, Homepage links, and endpoint verification remain consistent and protected
- the Ralph/OpenSpec loop has a stable contract for continued hardening rounds
