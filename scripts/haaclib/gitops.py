from __future__ import annotations

import re
from pathlib import Path

TRUTHY_VALUES = {"1", "true", "yes", "on"}


def render_env_placeholders(content: str, env: dict[str, str]) -> str:
    def replace(match: re.Match[str]) -> str:
        key = match.group(1)
        return env.get(key, match.group(0))

    return re.sub(r"\$\{([A-Z0-9_]+)\}", replace, content)


def render_values_file(values_template: Path, values_output: Path, env: dict[str, str]) -> None:
    content = values_template.read_text(encoding="utf-8")
    values_output.write_text(render_env_placeholders(content, env), encoding="utf-8")


def gitops_template_path(output_path: Path) -> Path:
    return output_path.with_name(f"{output_path.name}.template")


def falco_enabled(env: dict[str, str]) -> bool:
    value = env.get("HAAC_ENABLE_FALCO")
    if value is None:
        value = env.get("LXC_UNPRIVILEGED", "true")
        return value.strip().lower() not in TRUTHY_VALUES
    return value.strip().lower() in TRUTHY_VALUES


def falco_ingest_nodeport(env: dict[str, str]) -> int:
    raw_value = env.get("HAAC_FALCO_INGEST_NODEPORT", "32081").strip() or "32081"
    try:
        node_port = int(raw_value)
    except ValueError as exc:
        raise RuntimeError("HAAC_FALCO_INGEST_NODEPORT must be a valid integer node port") from exc
    if not 30000 <= node_port <= 32767:
        raise RuntimeError("HAAC_FALCO_INGEST_NODEPORT must be within the Kubernetes NodePort range 30000-32767")
    return node_port


def validate_falco_runtime_inputs(env: dict[str, str]) -> None:
    if not falco_enabled(env):
        return
    falco_ingest_nodeport(env)


def render_gitops_manifests(
    *,
    env: dict[str, str],
    outputs: tuple[Path, ...],
    falco_outputs: tuple[Path, ...],
    disabled_gitops_list: str,
) -> None:
    validate_falco_runtime_inputs(env)
    for output_path in outputs:
        template_path = gitops_template_path(output_path)
        if not template_path.exists():
            raise RuntimeError(f"Missing GitOps manifest template: {template_path}")
        if output_path in falco_outputs and not falco_enabled(env):
            output_path.write_text(disabled_gitops_list, encoding="utf-8")
            continue
        content = render_env_placeholders(template_path.read_text(encoding="utf-8"), env)
        output_path.write_text(content, encoding="utf-8")
