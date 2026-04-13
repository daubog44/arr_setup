#!/usr/bin/env python3
import argparse
import base64
import os
import tempfile
from pathlib import Path

from haaclib.authelia import resolve_admin_password_hash

CURRENT_DIR = Path(__file__).resolve().parent
ROOT_DIR = CURRENT_DIR.parent
TEMPLATE_DIR = ROOT_DIR / "k8s" / "charts" / "haac-stack" / "config-templates"


def load_env(env_path: Path) -> dict[str, str]:
    env: dict[str, str] = {}
    if not env_path.exists():
        return env

    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        env[key.strip()] = value.strip().strip('"').strip("'")
    return env


def read_oidc_key(env: dict[str, str], output_dir: Path) -> str:
    encoded_key = env.get("AUTHELIA_OIDC_PRIVATE_KEY_B64", "")
    if encoded_key:
        try:
            return base64.b64decode(encoded_key).decode("utf-8").strip()
        except Exception as exc:
            print(f"Error decoding AUTHELIA_OIDC_PRIVATE_KEY_B64: {exc}")

    candidates = [
        output_dir / "oidc_key.pem",
        Path(tempfile.gettempdir()) / "oidc_key.pem",
        Path("/tmp/oidc_key.pem"),
    ]
    for candidate in candidates:
        if candidate.exists():
            return candidate.read_text(encoding="utf-8").strip()

    return ""


def hydrate(
    template_path: Path,
    output_path: Path,
    env: dict[str, str],
    key_content: str,
) -> None:
    output_lines: list[str] = []

    for line in template_path.read_text(encoding="utf-8").splitlines(keepends=True):
        if "${INDENTED_OIDC_KEY}" in line:
            indent = " " * line.find("${INDENTED_OIDC_KEY}")
            for key_line in key_content.splitlines() or [""]:
                output_lines.append(f"{indent}{key_line}\n")
            continue

        rendered = line
        for key, value in env.items():
            rendered = rendered.replace(f"${{{key}}}", value)
        output_lines.append(rendered)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("".join(output_lines), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Hydrate Authelia templates from .env")
    parser.add_argument(
        "--env-file",
        default=str(ROOT_DIR / ".env"),
        help="Path to the .env file",
    )
    parser.add_argument(
        "--output-dir",
        default=tempfile.gettempdir(),
        help="Directory where hydrated files will be written",
    )
    args = parser.parse_args()

    env = load_env(Path(args.env_file))
    if "DOMAIN_NAME" in os.environ:
        env["DOMAIN_NAME"] = os.environ["DOMAIN_NAME"]
    env["AUTHELIA_ADMIN_PASSWORD_HASH"] = resolve_admin_password_hash(
        env,
        env_file=Path(args.env_file),
        wsl_distro=env.get("HAAC_WSL_DISTRO", "Debian"),
    )

    output_dir = Path(args.output_dir)
    key_content = read_oidc_key(env, output_dir)

    hydrate(
        TEMPLATE_DIR / "configuration.yml.template",
        output_dir / "authelia_configuration.yml",
        env,
        key_content,
    )
    hydrate(
        TEMPLATE_DIR / "users.yml.template",
        output_dir / "authelia_users.yml",
        env,
        key_content,
    )


if __name__ == "__main__":
    main()
