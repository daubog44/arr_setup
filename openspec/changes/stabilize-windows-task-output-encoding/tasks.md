## 1. Streaming contract

- [x] 1.1 Make `scripts/haac.py` stream `task` output with explicit UTF-8 decoding and replacement semantics
- [x] 1.2 Add a focused regression test for the `task-run` streaming path

## 2. Verification

- [x] 2.1 Validate with OpenSpec plus targeted unit tests
- [x] 2.2 Re-run the live bootstrap path far enough to confirm the wrapper now surfaces the real failing phase instead of crashing on decode
