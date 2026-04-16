from __future__ import annotations

import json
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


def load_worker_nodes(env: dict[str, str]) -> dict[str, dict]:
    raw_value = env.get("WORKER_NODES_JSON", "").strip()
    if not raw_value:
        raise RuntimeError("Missing required environment variable: WORKER_NODES_JSON")
    try:
        data = json.loads(raw_value)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"WORKER_NODES_JSON is not valid JSON: {exc}") from exc
    if not isinstance(data, dict):
        raise RuntimeError("WORKER_NODES_JSON must decode to an object keyed by worker name")
    return data


def falco_runtime_workers(env: dict[str, str]) -> list[str]:
    runtime_workers: list[str] = []
    for worker_name, worker_config in load_worker_nodes(env).items():
        labels = worker_config.get("labels", {})
        if not isinstance(labels, dict):
            raise RuntimeError(f"WORKER_NODES_JSON worker '{worker_name}' has non-object labels")
        value = labels.get("haac.io/falco-runtime")
        if value is not None and str(value).strip().lower() in TRUTHY_VALUES:
            runtime_workers.append(worker_name)
    return runtime_workers


def validate_falco_runtime_inputs(env: dict[str, str]) -> None:
    if not falco_enabled(env):
        return
    runtime_workers = falco_runtime_workers(env)
    if not runtime_workers:
        raise RuntimeError(
            "HAAC_ENABLE_FALCO=true requires at least one WORKER_NODES_JSON labels entry with "
            '"haac.io/falco-runtime":"true" so the Falco daemonset has a declared runtime target.'
        )


def render_gitops_manifests(
    *,
    env: dict[str, str],
    outputs: tuple[Path, ...],
    falco_output: Path,
    disabled_gitops_list: str,
) -> None:
    validate_falco_runtime_inputs(env)
    for output_path in outputs:
        template_path = gitops_template_path(output_path)
        if not template_path.exists():
            raise RuntimeError(f"Missing GitOps manifest template: {template_path}")
        if output_path == falco_output and not falco_enabled(env):
            output_path.write_text(disabled_gitops_list, encoding="utf-8")
            continue
        content = render_env_placeholders(template_path.read_text(encoding="utf-8"), env)
        output_path.write_text(content, encoding="utf-8")
