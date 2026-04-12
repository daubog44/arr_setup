#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

from haac import HaaCError, ROOT, merged_env, tool_location


DOCS_DIR = ROOT / "docs"
WORKLOGS_DIR = DOCS_DIR / "worklogs"
LOOP_PROMPT_PATH = DOCS_DIR / "haac-loop-prompt.md"
LOOP_REVIEW_PATH = DOCS_DIR / "loop-review.md"
LOOP_DISCOVERY_PATH = DOCS_DIR / "loop-discovery.md"
LOOP_SUBAGENTS_PATH = DOCS_DIR / "loop-subagents.md"
LOOP_WORKLOG_PATH = DOCS_DIR / "loop-worklog.md"
LOOP_CODEX_HOME = ROOT / ".codex-potter-home"
GLOBAL_CODEX_HOME = Path.home() / ".codex"
REPO_SKILLS_DIR = ROOT / ".codex" / "skills"
HOOKS_PATH = ROOT / ".codex" / "hooks.json"
CODEX_WRAPPER_PS1 = ROOT / "scripts" / "codex-wrapper.ps1"
CODEX_WRAPPER_CMD = ROOT / "scripts" / "codex-wrapper.cmd"
POTTER_PROJECTS_DIR = ROOT / ".codexpotter" / "projects"

REQUIRED_FILES = [
    ROOT / "AGENTS.md",
    ROOT / "README.md",
    ROOT / "ARCHITECTURE.md",
    ROOT / "Taskfile.yml",
    ROOT / "openspec" / "config.yaml",
    LOOP_PROMPT_PATH,
    LOOP_REVIEW_PATH,
    LOOP_DISCOVERY_PATH,
    LOOP_SUBAGENTS_PATH,
    LOOP_WORKLOG_PATH,
    DOCS_DIR / "worklogs" / "README.md",
    ROOT / ".codex" / "skills" / "openspec-apply-change" / "SKILL.md",
    ROOT / ".codex" / "skills" / "openspec-propose" / "SKILL.md",
    ROOT / ".codex" / "skills" / "haac-loop-review" / "SKILL.md",
    ROOT / ".codex" / "skills" / "haac-spec-discovery" / "SKILL.md",
    ROOT / ".codex" / "skills" / "haac-sidecar-subagents" / "SKILL.md",
    HOOKS_PATH,
    CODEX_WRAPPER_PS1,
    CODEX_WRAPPER_CMD,
]

REQUIRED_BINARIES = ["python", "git", "node", "npx", "codex", "codex-potter", "openspec"]


def run_command(
    command: list[str],
    *,
    cwd: Path = ROOT,
    env: dict[str, str] | None = None,
    check: bool = True,
    capture_output: bool = False,
    input_text: str | None = None,
) -> subprocess.CompletedProcess[str]:
    completed = subprocess.run(
        command,
        cwd=str(cwd),
        env=env,
        text=True,
        input=input_text,
        capture_output=capture_output,
        check=False,
    )
    if check and completed.returncode != 0:
        detail = (completed.stderr or completed.stdout or f"exit code {completed.returncode}").strip()
        raise HaaCError(f"Command failed: {' '.join(command)}\n{detail}")
    return completed


def slugify(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return slug or "session"


def relpath(path: Path) -> str:
    return path.resolve().relative_to(ROOT.resolve()).as_posix()


def executable(name: str) -> str:
    return tool_location(name) or name


def potter_verbosity() -> str:
    configured = merged_env().get("HAAC_POTTER_VERBOSITY", "minimal").strip().lower()
    if configured in {"minimal", "simple"}:
        return configured
    return "minimal"


def openspec_list() -> list[dict[str, object]]:
    completed = run_command([executable("openspec"), "list", "--json"], capture_output=True)
    payload = json.loads(completed.stdout or "{}")
    return list(payload.get("changes", []))


def active_changes() -> list[dict[str, object]]:
    changes = [change for change in openspec_list() if change.get("status") in {"in-progress", "ready"}]
    return sorted(changes, key=lambda item: str(item.get("lastModified", "")), reverse=True)


def select_changes_for_slug(slug: str, changes: list[dict[str, object]]) -> list[dict[str, object]]:
    slug_value = slugify(slug)
    if slug_value in {"", "session"}:
        return changes

    slug_tokens = [token for token in slug_value.split("-") if len(token) >= 3]
    selected: list[dict[str, object]] = []
    for change in changes:
        name = slugify(str(change.get("name", "")))
        if slug_value in name:
            selected.append(change)
            continue
        if slug_tokens and all(token in name for token in slug_tokens):
            selected.append(change)
            continue
        if slug_tokens and any(token in name for token in slug_tokens):
            selected.append(change)
    return selected


def validate_active_changes(changes: list[dict[str, object]]) -> None:
    for change in changes:
        name = str(change["name"])
        run_command([executable("openspec"), "validate", name])


def build_codex_config(env: dict[str, str]) -> str:
    lines = [
        'model = "gpt-5.4"',
        'model_reasoning_effort = "xhigh"',
        'personality = "pragmatic"',
        'service_tier = "fast"',
        'sandbox_mode = "danger-full-access"',
        "",
        '[mcp_servers.playwright]',
        'command = "npx"',
        'args = ["@playwright/mcp@latest", "--headless", "--isolated"]',
        "",
        '[mcp_servers.figma]',
        'url = "https://mcp.figma.com/mcp"',
        "",
        '[plugins."figma@openai-curated"]',
        "enabled = true",
        "",
        "[mcp_servers.github]",
        'url = "https://api.githubcopilot.com/mcp/"',
        'bearer_token_env_var = "GITHUB_PAT_TOKEN"',
        "",
        '[plugins."github@openai-curated"]',
        "enabled = true",
    ]
    return "\n".join(lines) + "\n"


def initialize_isolated_codex_home(env: dict[str, str]) -> Path:
    if LOOP_CODEX_HOME.exists():
        if LOOP_CODEX_HOME.is_file():
            raise HaaCError(f"Loop CODEX_HOME path is a file, not a directory: {LOOP_CODEX_HOME}")
        shutil.rmtree(LOOP_CODEX_HOME)
    LOOP_CODEX_HOME.mkdir(parents=True, exist_ok=True)

    if REPO_SKILLS_DIR.exists():
        shutil.copytree(REPO_SKILLS_DIR, LOOP_CODEX_HOME / "skills", dirs_exist_ok=True)

    for file_name in ("auth.json", "cap_sid"):
        source = GLOBAL_CODEX_HOME / file_name
        if source.exists():
            (LOOP_CODEX_HOME / file_name).write_bytes(source.read_bytes())

    config_path = LOOP_CODEX_HOME / "config.toml"
    config_path.write_text(build_codex_config(env), encoding="utf-8")
    return LOOP_CODEX_HOME


def build_runtime_env(use_global_home: bool) -> dict[str, str]:
    env = os.environ.copy()
    merged = merged_env()
    env.update(merged)
    if not use_global_home:
        env["CODEX_HOME"] = str(initialize_isolated_codex_home(merged))
    return env


def codex_bin(use_global_home: bool) -> str:
    if use_global_home:
        return executable("codex")
    return str(CODEX_WRAPPER_CMD)


def latest_potter_tracker() -> Path | None:
    if not POTTER_PROJECTS_DIR.exists():
        return None
    trackers = sorted(POTTER_PROJECTS_DIR.rglob("MAIN.md"), key=lambda path: path.stat().st_mtime, reverse=True)
    return trackers[0] if trackers else None


def latest_potter_project() -> Path | None:
    tracker = latest_potter_tracker()
    return tracker.parent if tracker else None


def read_jsonl(path: Path) -> list[dict[str, object]]:
    if not path.exists():
        return []
    entries: list[dict[str, object]] = []
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            payload = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(payload, dict):
            entries.append(payload)
    return entries


def normalize_rollout_path(value: str | None) -> Path | None:
    if not value:
        return None
    normalized = value
    if normalized.startswith("\\\\?\\"):
        normalized = normalized[4:]
    return Path(normalized)


def latest_rollout_session_path(project_dir: Path) -> Path | None:
    events = read_jsonl(project_dir / "potter-rollout.jsonl")
    for event in reversed(events):
        if event.get("type") != "round_configured":
            continue
        raw = event.get("rollout_path_raw") or event.get("rollout_path")
        if isinstance(raw, str):
            return normalize_rollout_path(raw)
    return None


def project_is_incomplete(project_dir: Path) -> bool:
    events = read_jsonl(project_dir / "potter-rollout.jsonl")
    if not events:
        return False
    event_types = [str(event.get("type")) for event in events]
    if "round_finished" in event_types or "project_succeeded" in event_types:
        return False
    return "round_configured" in event_types or "round_started" in event_types


def tail_lines(path: Path | None, limit: int = 40) -> str:
    if path is None or not path.exists():
        return ""
    lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    return "\n".join(lines[-limit:])


def project_diagnostics(project_dir: Path) -> str:
    rollout_file = project_dir / "potter-rollout.jsonl"
    rollout_tail = tail_lines(rollout_file, limit=20)
    session_path = latest_rollout_session_path(project_dir)
    session_tail = tail_lines(session_path, limit=60)
    sections = [f"project: {relpath(project_dir)}"]
    if rollout_tail:
        sections.append("potter-rollout tail:\n" + rollout_tail)
    if session_path and session_tail:
        sections.append(f"session log tail ({session_path.name}):\n" + session_tail)
    return "\n\n".join(sections)


def seal_stale_tracker() -> None:
    tracker = latest_potter_tracker()
    if tracker is None:
        return

    content = tracker.read_text(encoding="utf-8")
    if "status: initial" in content:
        return
    if "status: open" not in content and "finite_incantatem: false" not in content:
        return

    updated = content
    if "status: open" in updated:
        updated = updated.replace("status: open", "status: skip", 1)
    elif "status:" not in updated:
        updated = "status: skip\n" + updated

    if "finite_incantatem: false" in updated:
        updated = updated.replace("finite_incantatem: false", "finite_incantatem: true", 1)
    elif "finite_incantatem:" not in updated:
        updated = updated.replace("---\n\n", "---\nfinite_incantatem: true\n\n", 1)

    if updated != content:
        tracker.write_text(updated, encoding="utf-8")
        print(f"Sealed stale CodexPotter tracker: {relpath(tracker)}", flush=True)


def ensure_worklog(slug: str, mode: str, changes: list[dict[str, object]]) -> Path:
    now = datetime.now()
    day_dir = WORKLOGS_DIR / now.strftime("%Y-%m-%d")
    day_dir.mkdir(parents=True, exist_ok=True)
    worklog = day_dir / f"{now.strftime('%H%M')}-{slugify(slug)}.md"
    if worklog.exists():
        return worklog

    active_names = ", ".join(str(change["name"]) for change in changes) if changes else "none"
    worklog.write_text(
        "\n".join(
            [
                f"# {now.strftime('%Y-%m-%d %H:%M')} - {slugify(slug)}",
                "",
                f"- mode: {mode}",
                f"- active_changes: {active_names}",
                "- notes:",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    return worklog


def render_prompt(mode: str, slug: str, worklog: Path, changes: list[dict[str, object]]) -> str:
    base = LOOP_PROMPT_PATH.read_text(encoding="utf-8").rstrip()
    if changes:
        primary = str(changes[0]["name"])
        change_lines = [
            f"- `{change['name']}`: {change.get('completedTasks', 0)}/{change.get('totalTasks', 0)} tasks complete, status `{change.get('status')}`"
            for change in changes
        ]
    else:
        primary = "none"
        change_lines = ["- no active OpenSpec changes"]

    mode_block = [
        "## Current OpenSpec State",
        "",
        f"- primary change: `{primary}`",
        *change_lines,
        "",
        "## Session State",
        "",
        f"- mode: `{mode}`",
        f"- slug: `{slugify(slug)}`",
        f"- worklog: `{relpath(worklog)}`",
        "",
        "## Mode Contract",
        "",
    ]

    if mode == "discover":
        mode_block.extend(
            [
                "- perform narrow evidence-backed discovery only",
                "- create at most one new OpenSpec change if evidence meets the discovery policy",
                "- do not implement broad repo changes unless the smallest safe fix is already in scope",
            ]
        )
    else:
        mode_block.extend(
            [
                "- this mode is apply-first with autodiscovery and auto-improve fallback",
                "- use `openspec-apply-change` for the primary active change when tasks remain",
                "- if the active change finishes or no active change remains, switch to narrow discovery using the discovery policy",
                "- if the loop or repo is missing a required capability proven by evidence, open exactly one new change for that gap during this run",
            ]
        )

    mode_block.extend(
        [
            "",
            "## Mandatory Closeout",
            "",
            "- update the current worklog",
            "- update affected OpenSpec tasks or artifacts",
            "- report exact validation commands run and the furthest verified bootstrap phase",
        ]
    )

    return base + "\n\n" + "\n".join(mode_block) + "\n"


def codex_potter_command(rounds: int, use_global_home: bool) -> list[str]:
    return [
        executable("codex-potter"),
        "exec",
        "--codex-bin",
        codex_bin(use_global_home),
        "-m",
        "gpt-5.4",
        "-c",
        'model_reasoning_effort="xhigh"',
        "--rounds",
        str(rounds),
        "--verbosity",
        potter_verbosity(),
        "--sandbox",
        "danger-full-access",
        "--yolo",
    ]


def codex_potter_resume_command(project_file: Path, rounds: int, use_global_home: bool) -> list[str]:
    return [
        executable("codex-potter"),
        "resume",
        str(project_file),
        "--codex-bin",
        codex_bin(use_global_home),
        "-m",
        "gpt-5.4",
        "-c",
        'model_reasoning_effort="xhigh"',
        "--rounds",
        str(rounds),
        "--verbosity",
        potter_verbosity(),
        "--sandbox",
        "danger-full-access",
        "--yolo",
    ]


def run_potter_rollout(command: list[str], env: dict[str, str], prompt: str, rounds: int, use_global_home: bool) -> None:
    completed = subprocess.run(
        command,
        cwd=str(ROOT),
        env=env,
        text=True,
        input=prompt,
        check=False,
    )
    if completed.returncode == 0:
        return

    project_dir = latest_potter_project()
    if project_dir and project_is_incomplete(project_dir):
        project_file = project_dir / "MAIN.md"
        print(
            "CodexPotter exited before closing the round. "
            f"Attempting resume for {relpath(project_file)}.",
            flush=True,
        )
        resumed = subprocess.run(
            codex_potter_resume_command(project_file, rounds, use_global_home),
            cwd=str(ROOT),
            env=env,
            text=True,
            check=False,
        )
        if resumed.returncode == 0:
            return
        detail = project_diagnostics(project_dir)
        raise HaaCError(
            "CodexPotter rollout failed after automatic resume.\n"
            f"exit code: {resumed.returncode}\n\n{detail}"
        )

    detail = f"exit code: {completed.returncode}"
    if project_dir:
        detail += "\n\n" + project_diagnostics(project_dir)
    raise HaaCError("CodexPotter rollout failed.\n" + detail)


def check_loop(use_global_home: bool) -> None:
    failures: list[str] = []

    print("HaaC Ralph loop bootstrap check", flush=True)
    for path in REQUIRED_FILES:
        if path.exists():
            print(f"[ok] file: {relpath(path)}", flush=True)
        else:
            print(f"[missing] file: {relpath(path)}", flush=True)
            failures.append(relpath(path))

    for binary in REQUIRED_BINARIES:
        location = tool_location(binary)
        if location:
            print(f"[ok] binary {binary}: {location}", flush=True)
        else:
            print(f"[missing] binary {binary}", flush=True)
            failures.append(binary)

    run_command([sys.executable, str(ROOT / "scripts" / "haac.py"), "doctor"])
    changes = active_changes()
    print(f"[ok] openspec active changes discovered: {len(changes)}", flush=True)
    if changes:
        validate_active_changes(changes)
        print("[ok] active OpenSpec changes validated", flush=True)
    else:
        print("[warn] no active OpenSpec changes; loop will run in discovery mode", flush=True)

    if use_global_home:
        if GLOBAL_CODEX_HOME.exists():
            print(f"[ok] global CODEX_HOME: {GLOBAL_CODEX_HOME}", flush=True)
        else:
            print(f"[missing] global CODEX_HOME: {GLOBAL_CODEX_HOME}", flush=True)
            failures.append("global-codex-home")

    if failures:
        raise HaaCError("Loop bootstrap check failed: " + ", ".join(failures))


def codex_preflight(env: dict[str, str], use_global_home: bool) -> None:
    prompt = (
        "Do not modify files. Do not implement tasks. Run only a technical preflight.\n\n"
        "Check these items:\n"
        "1. GitHub MCP: retrieve the authenticated user or a minimal repository list.\n"
        "2. OpenSpec CLI: run `openspec list --json`.\n"
        "3. Repo bootstrap: run `python scripts/haac.py doctor`.\n\n"
        "If all pass, print exactly one line starting with PRECHECK_OK:.\n"
        "If anything fails, print exactly one line starting with PRECHECK_FAIL:.\n"
        "Print nothing else."
    )
    print("Running Codex preflight (GitHub MCP, OpenSpec CLI, repo doctor)...", flush=True)
    process = subprocess.Popen(
        codex_potter_command(1, use_global_home),
        cwd=str(ROOT),
        env=env,
        text=True,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    assert process.stdin is not None
    process.stdin.write(prompt)
    process.stdin.close()

    start = time.monotonic()
    heartbeat_seconds = 15
    timeout_seconds = 300
    while True:
        try:
            stdout, stderr = process.communicate(timeout=heartbeat_seconds)
            break
        except subprocess.TimeoutExpired:
            elapsed = int(time.monotonic() - start)
            print(f"Codex preflight still running... {elapsed}s", flush=True)
            if elapsed >= timeout_seconds:
                process.kill()
                stdout, stderr = process.communicate()
                output = (stdout or "") + (stderr or "")
                raise HaaCError(
                    "Codex preflight timed out after "
                    f"{timeout_seconds}s.\nLast output:\n{output.strip()}"
                )

    output = (stdout or "") + (stderr or "")
    if "PRECHECK_OK:" in output and process.returncode == 0:
        print("Codex preflight ok.", flush=True)
        return
    raise HaaCError("Codex preflight failed.\n" + output.strip())


def effective_mode(mode: str, changes: list[dict[str, object]]) -> str:
    if mode == "apply" and not changes:
        return "discover"
    return mode


def run_loop(slug: str, rounds: int, mode: str, use_global_home: bool, with_preflight: bool, dry_run: bool) -> None:
    check_loop(use_global_home)
    seal_stale_tracker()
    all_changes = active_changes()
    changes = select_changes_for_slug(slug, all_changes)
    if all_changes and not changes:
        print(
            f"No active OpenSpec change matched slug '{slugify(slug)}'; "
            "this run will use discovery for that scope.",
            flush=True,
        )
    worklog = ensure_worklog(slug, mode, changes)
    session_mode = effective_mode(mode, changes)
    prompt = render_prompt(session_mode, slug, worklog, changes)
    command = codex_potter_command(rounds, use_global_home)

    if dry_run:
        print("Dry run only.", flush=True)
        print("Command:", flush=True)
        print(" ".join(command), flush=True)
        print("", flush=True)
        print(prompt, flush=True)
        return

    env = build_runtime_env(use_global_home)
    if with_preflight:
        codex_preflight(env, use_global_home)

    print(f"Starting CodexPotter rollout with up to {rounds} rounds in {session_mode} mode.", flush=True)
    run_potter_rollout(command, env, prompt, rounds, use_global_home)


def cmd_check(args: argparse.Namespace) -> None:
    check_loop(args.use_global_home)


def cmd_worklog(args: argparse.Namespace) -> None:
    path = ensure_worklog(args.slug, args.mode, active_changes())
    print(relpath(path))


def cmd_prompt(args: argparse.Namespace) -> None:
    worklog = ensure_worklog(args.slug, args.mode, active_changes())
    print(render_prompt(args.mode, args.slug, worklog, active_changes()))


def cmd_run(args: argparse.Namespace) -> None:
    run_loop(args.slug, args.rounds, args.mode, args.use_global_home, args.with_preflight, args.dry_run)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="OpenSpec-first Ralph loop bootstrap for HaaC")
    subparsers = parser.add_subparsers(dest="command", required=True)

    command = subparsers.add_parser("check")
    command.add_argument("--use-global-home", action="store_true")
    command.set_defaults(func=cmd_check)

    command = subparsers.add_parser("worklog")
    command.add_argument("--slug", default="session")
    command.add_argument("--mode", choices=["apply", "discover"], default="apply")
    command.set_defaults(func=cmd_worklog)

    command = subparsers.add_parser("prompt")
    command.add_argument("--slug", default="session")
    command.add_argument("--mode", choices=["apply", "discover"], default="apply")
    command.set_defaults(func=cmd_prompt)

    command = subparsers.add_parser("run")
    command.add_argument("--slug", default="session")
    command.add_argument("--rounds", type=int, default=10)
    command.add_argument("--mode", choices=["apply", "discover"], default="apply")
    command.add_argument("--use-global-home", action="store_true")
    command.add_argument("--with-preflight", action="store_true")
    command.add_argument("--dry-run", action="store_true")
    command.set_defaults(func=cmd_run)

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    try:
        args.func(args)
    except HaaCError as exc:
        print(str(exc), file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print("Interrupted.", file=sys.stderr)
        return 130
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
