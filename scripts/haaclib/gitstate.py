from __future__ import annotations

import subprocess
from pathlib import Path
from urllib.parse import urlparse


def is_git_repo(root: Path) -> bool:
    return (root / ".git").exists()


def git_has_remote(root: Path, remote_name: str = "origin") -> bool:
    if not is_git_repo(root):
        return False
    completed = subprocess.run(
        ["git", "remote", "get-url", remote_name],
        cwd=str(root),
        text=True,
        capture_output=True,
        check=False,
    )
    return completed.returncode == 0


def git_remote_url(root: Path, remote_name: str = "origin") -> str:
    completed = subprocess.run(
        ["git", "remote", "get-url", remote_name],
        cwd=str(root),
        text=True,
        capture_output=True,
        check=True,
    )
    return completed.stdout.strip()


def normalize_git_remote_url(url: str) -> str:
    candidate = url.strip()
    if not candidate:
        return ""
    if "://" not in candidate and ":" in candidate and "@" in candidate.split(":", 1)[0]:
        user_host, path = candidate.split(":", 1)
        candidate = f"ssh://{user_host}/{path}"
    parsed = urlparse(candidate)
    host = (parsed.hostname or "").lower()
    port = f":{parsed.port}" if parsed.port else ""
    path = parsed.path.rstrip("/")
    if path.endswith(".git"):
        path = path[:-4]
    username = parsed.username or ""
    if parsed.scheme == "ssh":
        user_prefix = f"{username}@" if username else ""
        return f"ssh://{user_prefix}{host}{port}{path}"
    return f"https://{host}{port}{path}"


def git_status_entries(root: Path) -> list[tuple[str, str]]:
    completed = subprocess.run(
        ["git", "status", "--porcelain"],
        cwd=str(root),
        text=True,
        capture_output=True,
        check=False,
    )
    status = completed.stdout or ""
    entries: list[tuple[str, str]] = []
    for line in status.splitlines():
        if not line.strip():
            continue
        state = line[:2]
        path = line[3:] if len(line) > 3 else line
        if " -> " in path:
            path = path.split(" -> ", 1)[1]
        entries.append((state, path.strip()))
    return entries


def git_dirty_paths(root: Path) -> list[str]:
    return [path for _, path in git_status_entries(root)]


def git_tracked_dirty_paths(root: Path) -> list[str]:
    return [path for state, path in git_status_entries(root) if state != "??"]


def git_untracked_paths(root: Path) -> list[str]:
    return [path for state, path in git_status_entries(root) if state == "??"]


def git_head(root: Path, ref: str) -> str:
    completed = subprocess.run(
        ["git", "rev-parse", ref],
        cwd=str(root),
        text=True,
        capture_output=True,
        check=True,
    )
    return completed.stdout.strip()


def git_ref_state(root: Path, local_ref: str, remote_ref: str) -> str:
    if git_head(root, local_ref) == git_head(root, remote_ref):
        return "equal"
    local_has_remote = (
        subprocess.run(
            ["git", "merge-base", "--is-ancestor", remote_ref, local_ref],
            cwd=str(root),
            text=True,
            capture_output=True,
            check=False,
        ).returncode
        == 0
    )
    remote_has_local = (
        subprocess.run(
            ["git", "merge-base", "--is-ancestor", local_ref, remote_ref],
            cwd=str(root),
            text=True,
            capture_output=True,
            check=False,
        ).returncode
        == 0
    )
    if local_has_remote and not remote_has_local:
        return "ahead"
    if remote_has_local and not local_has_remote:
        return "behind"
    return "diverged"
