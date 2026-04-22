## 1. Contracts

- [x] 1.1 Add OpenSpec delta(s) for the Cobra-only supported operator surface

## 2. Wrapper Boundary

- [x] 2.1 Remove Python fallback from `haac.ps1` and `haac.sh`
- [x] 2.2 Stop using `go run` as the steady-state wrapper execution path and bootstrap a repo-local `haac` binary instead
- [x] 2.3 Remove the hidden Cobra `legacy` command and any help text that still treats Python as a supported runtime fallback

## 3. Migration Execution

- [x] 3.1 Port the supported operator command surface needed by `up`, `down`, preflight, and tool bootstrap away from direct Python CLI ownership
- [x] 3.2 Update Taskfiles and docs so the supported operator path no longer documents `scripts/haac.py` as the primary CLI
- [x] 3.3 Record the remaining non-operator Python surfaces explicitly if any loop-only or maintenance-only scripts stay out of scope

## 4. Validation

- [x] 4.1 Validate with OpenSpec and Go tests
- [x] 4.2 Smoke-test the wrapper path without Python fallback
- [x] 4.3 Confirm the steady-state wrapper path runs the repo-local binary rather than recompiling on every invocation
