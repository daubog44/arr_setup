#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path


BEGIN_MARKER = "# BEGIN HAAC MANAGED LXC HARDWARE"
END_MARKER = "# END HAAC MANAGED LXC HARDWARE"
LEGACY_PATTERNS = (
    re.compile(r"^lxc\.idmap:"),
    re.compile(r"^lxc\.cgroup2\.devices\.allow:"),
    re.compile(r"^lxc\.mount\.entry: /dev/"),
    re.compile(r"^lxc\.mount\.entry: /usr/lib/"),
    re.compile(r"^lxc\.mount\.entry: /usr/bin/nvidia"),
    re.compile(r"^lxc\.apparmor\.profile:"),
    re.compile(r"^lxc\.cap\.drop:"),
    re.compile(r"^lxc\.mount\.auto:"),
    re.compile(r"^lxc\.mount\.entry: /sys/kernel/debug"),
    re.compile(r"^lxc\.mount\.entry: /sys/kernel/btf"),
    re.compile(r"^lxc\.mount\.entry: .* data none bind,create=dir$"),
)


def parse_managed_lines(raw_json: str) -> list[str]:
    values = json.loads(raw_json)
    if not isinstance(values, list) or not values or any(not isinstance(item, str) for item in values):
        raise ValueError("HAAC_LXC_MANAGED_CONFIG_JSON must be a non-empty JSON array of strings")
    return values


def is_managed_legacy_line(line: str) -> bool:
    return any(pattern.search(line) for pattern in LEGACY_PATTERNS)


def reconcile_lxc_config_text(text: str, managed_lines: list[str]) -> str:
    original_lines = text.splitlines()
    marker_indexes = [
        index
        for index, line in enumerate(original_lines)
        if line in (BEGIN_MARKER, END_MARKER)
    ]
    managed_line_indexes = [index for index, line in enumerate(original_lines) if is_managed_legacy_line(line)]
    preserved_lines = [
        line
        for line in original_lines
        if line not in (BEGIN_MARKER, END_MARKER) and not is_managed_legacy_line(line)
    ]
    block_lines = [BEGIN_MARKER, *managed_lines, END_MARKER]
    insertion_candidates = marker_indexes + managed_line_indexes
    if insertion_candidates:
        insert_source_index = min(insertion_candidates)
        insert_at = sum(
            1
            for line in original_lines[:insert_source_index]
            if line not in (BEGIN_MARKER, END_MARKER) and not is_managed_legacy_line(line)
        )
    else:
        insert_at = len(preserved_lines)
    new_lines = preserved_lines[:insert_at] + block_lines + preserved_lines[insert_at:]
    new_text = "\n".join(new_lines)
    if text.endswith("\n"):
        new_text += "\n"
    return new_text


def reconcile_lxc_config_file(config_path: Path, managed_lines: list[str]) -> bool:
    text = config_path.read_text(encoding="utf-8")
    new_text = reconcile_lxc_config_text(text, managed_lines)
    if new_text == text:
        return False
    config_path.write_text(new_text, encoding="utf-8")
    return True


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Reconcile the HAAC-managed hardware block in a Proxmox LXC config")
    parser.add_argument("config_path", type=Path)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    raw_json = os.environ.get("HAAC_LXC_MANAGED_CONFIG_JSON")
    if raw_json is None:
        print("HAAC_LXC_MANAGED_CONFIG_JSON is required", file=sys.stderr)
        return 1
    try:
        managed_lines = parse_managed_lines(raw_json)
        changed = reconcile_lxc_config_file(args.config_path, managed_lines)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(str(exc), file=sys.stderr)
        return 1
    print("changed" if changed else "unchanged")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
