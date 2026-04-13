from __future__ import annotations

import os
from pathlib import Path


def resolve_ssh_host_key_mode(env: dict[str, str] | None) -> str:
    mode = (env or {}).get("HAAC_SSH_HOST_KEY_CHECKING", "").strip().lower()
    if mode not in {"accept-new", "yes", "no"}:
        return "accept-new"
    return mode


def resolve_known_hosts_path(root: Path, env: dict[str, str] | None) -> Path:
    override = (env or {}).get("HAAC_SSH_KNOWN_HOSTS_PATH", "").strip()
    if override:
        candidate = Path(override)
        if not candidate.is_absolute():
            candidate = (root / candidate).resolve()
        return candidate
    return root / ".ssh" / "known_hosts"


def ensure_known_hosts_file(path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists():
        path.write_text("", encoding="utf-8")
        try:
            os.chmod(path, 0o600)
        except OSError:
            pass
    return path

