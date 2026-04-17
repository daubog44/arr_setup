## Context

`scripts/haac.py` owns the official `task-run` wrapper that prints live `task` output and extracts the bootstrap phase history for recovery summaries. Today `run_task_with_output()` uses `subprocess.Popen(..., text=True)` without an explicit encoding. On Windows that falls back to the active code page, which is not guaranteed to decode UTF-8 bytes emitted by WSL/Ansible/systemd output.

The live failure is not theoretical. A targeted reproduction against the same repo/runtime path produced:

- `UnicodeDecodeError: 'charmap' codec can't decode byte 0x8f ...` from Python's `_readerthread`
- while the round was trying to surface `k3s-agent`/flannel diagnostics from the real cluster

That makes the operator output lie by omission: the local wrapper crashes before the real failing phase and evidence bundle are fully printed.

## Goals / Non-Goals

**Goals:**

- Make `task-run` output streaming use a deterministic UTF-8 contract on Windows.
- Preserve incremental line printing plus phase extraction behavior.
- Add a regression test that would have failed with the locale-dependent implementation.

**Non-Goals:**

- Redesign task execution or replace the Task runner.
- Normalize every subprocess in the repo to UTF-8 in this wave.
- Change Ansible or K3s diagnostics themselves.

## Decisions

### Use explicit UTF-8 decoding in the streaming `Popen` path

`run()` already enforces `encoding="utf-8", errors="replace"` for most subprocess calls. `run_task_with_output()` should follow the same contract instead of relying on the process locale. This is the smallest fix because it addresses the exact blind spot without changing upstream tools.

### Prefer `errors="replace"` over strict decoding

The operator path values availability over perfect fidelity for arbitrary bytes. Replacement characters keep the stream readable, preserve line structure, and allow the bootstrap phase/failure summary logic to complete even when a remote tool emits malformed or mixed-encoding bytes.

### Capture the contract with a focused mock-based regression test

The regression only needs to prove that `Popen` is configured for UTF-8 streaming. Mock-based coverage is enough because the bug was caused by constructor arguments, not by downstream parsing logic.

## Risks / Trade-offs

- [Risk] Replacement decoding can hide the exact original byte sequence.  
  [Mitigation] The operator still sees readable diagnostics instead of losing the entire failure payload.
- [Risk] This wave does not fix every possible locale-dependent subprocess in the repo.  
  [Mitigation] It fixes the official `task-run` surface that gates the bootstrap ladder and browser verification loop.
