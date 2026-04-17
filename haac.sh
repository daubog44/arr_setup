#!/usr/bin/env sh
set -eu

SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)

if command -v python3 >/dev/null 2>&1; then
  PYTHON_BIN=python3
elif command -v python >/dev/null 2>&1; then
  PYTHON_BIN=python
else
  echo "python3 or python is required" >&2
  exit 1
fi

for arg in "$@"; do
  case "$arg" in
    internal:*)
      echo "internal:* Task targets are not part of the supported haac operator surface; use a public task instead" >&2
      exit 1
      ;;
  esac
done

if command -v go >/dev/null 2>&1; then
  cd "$SCRIPT_DIR"
  if go run ./cmd/haac "$@"; then
    exit 0
  fi
  echo "warning: Go/Cobra entrypoint failed; falling back to the Python bridge." >&2
fi

exec "$PYTHON_BIN" "$SCRIPT_DIR/scripts/haac.py" task-run -- "$@"
