from __future__ import annotations

import subprocess
import sys
from pathlib import Path


def _crypt_hash(password: str) -> str:
    import crypt

    return crypt.crypt(password, crypt.mksalt(crypt.METHOD_SHA512))


def _crypt_verify(password: str, existing_hash: str) -> bool:
    import crypt

    return crypt.crypt(password, existing_hash) == existing_hash


def _run_wsl_crypt(password: str, existing_hash: str | None, distro: str) -> str | bool:
    check_mode = "verify" if existing_hash else "hash"
    code = (
        "import crypt, sys\n"
        "mode = sys.argv[1]\n"
        "password = sys.argv[2]\n"
        "existing = sys.argv[3] if len(sys.argv) > 3 else ''\n"
        "if mode == 'verify':\n"
        "    raise SystemExit(0 if crypt.crypt(password, existing) == existing else 1)\n"
        "print(crypt.crypt(password, crypt.mksalt(crypt.METHOD_SHA512)))\n"
    )
    command = ["wsl", "-d", distro, "--", "python3", "-c", code, check_mode, password]
    if existing_hash:
        command.append(existing_hash)
    completed = subprocess.run(
        command,
        text=True,
        encoding="utf-8",
        errors="replace",
        capture_output=True,
        check=False,
    )
    if check_mode == "verify":
        return completed.returncode == 0
    if completed.returncode != 0:
        detail = (completed.stderr or completed.stdout or f"exit code {completed.returncode}").strip()
        raise RuntimeError(f"Unable to hash AUTHELIA_ADMIN_PASSWORD via WSL python3.\n{detail}")
    return completed.stdout.strip()


def verify_password_against_hash(password: str, existing_hash: str, *, wsl_distro: str | None = None) -> bool:
    try:
        return _crypt_verify(password, existing_hash)
    except (ImportError, AttributeError):
        if sys.platform.startswith("win") and wsl_distro:
            return bool(_run_wsl_crypt(password, existing_hash, wsl_distro))
        raise RuntimeError("Unable to verify AUTHELIA_ADMIN_PASSWORD_HASH: crypt support is unavailable.")


def hash_password(password: str, *, wsl_distro: str | None = None) -> str:
    try:
        return _crypt_hash(password)
    except (ImportError, AttributeError):
        if sys.platform.startswith("win") and wsl_distro:
            return str(_run_wsl_crypt(password, None, wsl_distro))
        raise RuntimeError("Unable to hash AUTHELIA_ADMIN_PASSWORD: crypt support is unavailable.")


def persist_env_value(env_file: Path, key: str, value: str) -> None:
    if not env_file.exists():
        return
    lines = env_file.read_text(encoding="utf-8").splitlines()
    rendered = f'{key}="{value}"'
    updated = False
    for index, line in enumerate(lines):
        if line.startswith(f"{key}="):
            lines[index] = rendered
            updated = True
            break
    if not updated:
        lines.append(rendered)
    env_file.write_text("\n".join(lines) + "\n", encoding="utf-8")


def resolve_admin_password_hash(
    env: dict[str, str],
    *,
    env_file: Path | None = None,
    wsl_distro: str | None = None,
) -> str:
    explicit_password = env.get("AUTHELIA_ADMIN_PASSWORD", "").strip()
    existing_hash = env.get("AUTHELIA_ADMIN_PASSWORD_HASH", "").strip()
    if not explicit_password:
        return existing_hash
    if existing_hash:
        try:
            if verify_password_against_hash(explicit_password, existing_hash, wsl_distro=wsl_distro):
                return existing_hash
        except RuntimeError:
            pass
    new_hash = hash_password(explicit_password, wsl_distro=wsl_distro)
    if env_file is not None:
        persist_env_value(env_file, "AUTHELIA_ADMIN_PASSWORD_HASH", new_hash)
    return new_hash
