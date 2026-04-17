from __future__ import annotations

import re


SAFE_USERNAME_RE = re.compile(r"^[A-Za-z0-9._-]+$")
SAFE_INLINE_VALUE_RE = re.compile(r'^[^\r\n"]+$')
TRUTHY_VALUES = {"1", "true", "yes", "on"}
FALSY_VALUES = {"", "0", "false", "no", "off"}


def env_value(env: dict[str, str], key: str) -> str:
    return str(env.get(key, "")).strip()


def set_default(env: dict[str, str], key: str, value: str) -> None:
    if value and not env_value(env, key):
        env[key] = value


def env_flag(env: dict[str, str], key: str) -> bool:
    value = env_value(env, key).lower()
    if value not in TRUTHY_VALUES | FALSY_VALUES:
        raise ValueError(f"{key} must be one of: 1, true, yes, on, 0, false, no, off.")
    return value in TRUTHY_VALUES


def shared_downloader_credentials_enabled(env: dict[str, str]) -> bool:
    return env_flag(env, "HAAC_ENABLE_SHARED_DOWNLOADER_CREDENTIALS")


def validate_identity_value(key: str, value: str, *, pattern: re.Pattern[str], hint: str) -> None:
    if value and not pattern.fullmatch(value):
        raise ValueError(f"{key} contains unsupported characters. {hint}")


def apply_identity_defaults(env: dict[str, str]) -> dict[str, str]:
    main_username = env_value(env, "HAAC_MAIN_USERNAME")
    main_password = env_value(env, "HAAC_MAIN_PASSWORD")
    main_email = env_value(env, "HAAC_MAIN_EMAIL")
    main_name = env_value(env, "HAAC_MAIN_NAME")
    shared_downloader_credentials = shared_downloader_credentials_enabled(env)

    if main_username:
        for key in (
            "AUTHELIA_ADMIN_USERNAME",
            "ARGOCD_USERNAME",
            "GRAFANA_ADMIN_USERNAME",
            "LITMUS_ADMIN_USERNAME",
            "SEMAPHORE_ADMIN_USERNAME",
        ):
            set_default(env, key, main_username)

    if main_password:
        for key in (
            "AUTHELIA_ADMIN_PASSWORD",
            "ARGOCD_PASSWORD",
            "GRAFANA_ADMIN_PASSWORD",
            "LITMUS_ADMIN_PASSWORD",
            "SEMAPHORE_ADMIN_PASSWORD",
        ):
            set_default(env, key, main_password)

    set_default(env, "AUTHELIA_ADMIN_USERNAME", "admin")
    authelia_username = env_value(env, "AUTHELIA_ADMIN_USERNAME") or "admin"

    for key in ("ARGOCD_USERNAME", "GRAFANA_ADMIN_USERNAME", "LITMUS_ADMIN_USERNAME", "SEMAPHORE_ADMIN_USERNAME"):
        set_default(env, key, authelia_username)

    if env_value(env, "AUTHELIA_ADMIN_PASSWORD"):
        for key in (
            "ARGOCD_PASSWORD",
            "GRAFANA_ADMIN_PASSWORD",
            "LITMUS_ADMIN_PASSWORD",
            "SEMAPHORE_ADMIN_PASSWORD",
        ):
            set_default(env, key, env_value(env, "AUTHELIA_ADMIN_PASSWORD"))

    if main_email:
        set_default(env, "AUTHELIA_ADMIN_EMAIL", main_email)
        set_default(env, "SEMAPHORE_ADMIN_EMAIL", main_email)

    domain_name = env_value(env, "DOMAIN_NAME")
    if domain_name:
        set_default(env, "AUTHELIA_ADMIN_EMAIL", f"{authelia_username}@{domain_name}")
        set_default(env, "SEMAPHORE_ADMIN_EMAIL", f"{authelia_username}@{domain_name}")
    set_default(env, "SEMAPHORE_ADMIN_EMAIL", "admin@localhost")

    if main_name:
        set_default(env, "AUTHELIA_ADMIN_NAME", main_name)
        set_default(env, "SEMAPHORE_ADMIN_NAME", main_name)

    set_default(env, "AUTHELIA_ADMIN_NAME", "Administrator")
    set_default(env, "SEMAPHORE_ADMIN_NAME", env_value(env, "AUTHELIA_ADMIN_NAME") or "Administrator")

    if shared_downloader_credentials:
        set_default(env, "QBITTORRENT_USERNAME", main_username)
        set_default(env, "QUI_PASSWORD", main_password)

    for key in (
        "HAAC_MAIN_USERNAME",
        "AUTHELIA_ADMIN_USERNAME",
        "ARGOCD_USERNAME",
        "GRAFANA_ADMIN_USERNAME",
        "LITMUS_ADMIN_USERNAME",
        "SEMAPHORE_ADMIN_USERNAME",
        "QBITTORRENT_USERNAME",
    ):
        validate_identity_value(
            key,
            env_value(env, key),
            pattern=SAFE_USERNAME_RE,
            hint="Use only letters, digits, dot, underscore, or dash.",
        )

    for key in ("HAAC_MAIN_NAME", "AUTHELIA_ADMIN_NAME", "SEMAPHORE_ADMIN_NAME", "AUTHELIA_ADMIN_EMAIL", "SEMAPHORE_ADMIN_EMAIL"):
        validate_identity_value(
            key,
            env_value(env, key),
            pattern=SAFE_INLINE_VALUE_RE,
            hint='Double quotes and line breaks are not supported here.',
        )

    return env
