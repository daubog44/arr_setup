from __future__ import annotations

import base64
import json
from pathlib import Path


def render_secret_manifest(
    name: str,
    namespace: str,
    *,
    literals: dict[str, str] | None = None,
    files: dict[str, Path] | None = None,
) -> str:
    lines = [
        "apiVersion: v1",
        "kind: Secret",
        "metadata:",
        f"  name: {name}",
        f"  namespace: {namespace}",
        "type: Opaque",
    ]

    literal_items = literals or {}
    if literal_items:
        lines.append("stringData:")
        for key, value in literal_items.items():
            lines.append(f"  {key}: {json.dumps(value)}")

    file_items = files or {}
    if file_items:
        lines.append("data:")
        for key, path in file_items.items():
            encoded = base64.b64encode(path.read_bytes()).decode("ascii")
            lines.append(f"  {key}: {encoded}")

    return "\n".join(lines) + "\n"
