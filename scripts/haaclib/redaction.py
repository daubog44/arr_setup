from __future__ import annotations

from collections.abc import Iterable


SECRET_KEY_HINTS = (
    "PASSWORD",
    "SECRET",
    "TOKEN",
    "PRIVATE_KEY",
    "ENCRYPTION",
    "JWT",
    "OIDC",
    "HASH",
)


def secret_values_from_env(env: dict[str, str] | None) -> list[str]:
    if not env:
        return []
    values: set[str] = set()
    for key, value in env.items():
        if not value or len(value) < 4:
            continue
        upper_key = key.upper()
        if any(hint in upper_key for hint in SECRET_KEY_HINTS):
            values.add(value)
    return sorted(values, key=len, reverse=True)


def redact_sensitive_text(text: str, values: Iterable[str]) -> str:
    redacted = text
    for value in values:
        if value:
            redacted = redacted.replace(value, "***REDACTED***")
    return redacted

