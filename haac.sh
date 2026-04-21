#!/usr/bin/env sh
set -eu

SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)

host_platform() {
  uname_s=$(uname -s | tr '[:upper:]' '[:lower:]')
  case "$uname_s" in
    linux*) printf '%s\n' "linux" ;;
    darwin*) printf '%s\n' "darwin" ;;
    *) echo "unsupported platform for haac: $uname_s" >&2; exit 1 ;;
  esac
}

host_arch() {
  uname_m=$(uname -m | tr '[:upper:]' '[:lower:]')
  case "$uname_m" in
    x86_64|amd64) printf '%s\n' "amd64" ;;
    arm64|aarch64) printf '%s\n' "arm64" ;;
    *) echo "unsupported architecture for haac: $uname_m" >&2; exit 1 ;;
  esac
}

haac_binary_path() {
  printf '%s/.tools/%s-%s/bin/haac\n' "$SCRIPT_DIR" "$(host_platform)" "$(host_arch)"
}

haac_binary_stale() {
  binary=$1
  if [ ! -x "$binary" ]; then
    return 0
  fi

  for source in "$SCRIPT_DIR/go.mod" "$SCRIPT_DIR/go.sum"; do
    if [ -f "$source" ] && [ "$source" -nt "$binary" ]; then
      return 0
    fi
  done

  if find "$SCRIPT_DIR/cmd" "$SCRIPT_DIR/internal" -type f -newer "$binary" -print -quit 2>/dev/null | grep -q .; then
    return 0
  fi
  return 1
}

ensure_haac_binary() {
  binary=$(haac_binary_path)
  if [ -x "$binary" ] && ! haac_binary_stale "$binary"; then
    printf '%s\n' "$binary"
    return 0
  fi

  if ! command -v go >/dev/null 2>&1; then
    echo "repo-local haac binary not found at $binary and Go is unavailable. Install Go or build cmd/haac first." >&2
    exit 1
  fi

  mkdir -p "$(dirname "$binary")"
  (
    cd "$SCRIPT_DIR"
    go build -o "$binary" ./cmd/haac
  )
  if [ ! -x "$binary" ]; then
    echo "failed to build repo-local haac binary at $binary" >&2
    exit 1
  fi
  printf '%s\n' "$binary"
}

for arg in "$@"; do
  case "$arg" in
    internal:*)
      echo "internal:* Task targets are not part of the supported haac operator surface; use a public task instead" >&2
      exit 1
      ;;
  esac
done

HAAC_BIN=$(ensure_haac_binary)
exec "$HAAC_BIN" "$@"
