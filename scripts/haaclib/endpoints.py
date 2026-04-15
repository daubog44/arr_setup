from __future__ import annotations

import re
import urllib.error
import urllib.request
from pathlib import Path


def endpoint_specs_source_path(values_output: Path, values_template: Path) -> Path:
    if values_output.exists():
        return values_output
    if values_template.exists():
        return values_template
    raise RuntimeError("Missing values source of truth for public endpoint verification")


def load_endpoint_specs(values_output: Path, values_template: Path, domain_name: str) -> list[dict[str, str]]:
    source_path = endpoint_specs_source_path(values_output, values_template)
    lines = source_path.read_text(encoding="utf-8").splitlines()
    in_ingresses = False
    current_name = ""
    current: dict[str, str] = {}
    endpoints: list[dict[str, str]] = []

    def flush_current() -> None:
        nonlocal current_name, current
        if not current_name or "subdomain" not in current:
            current_name = ""
            current = {}
            return
        enabled = current.get("enabled", "true").strip().lower() not in {"0", "false", "no", "off"}
        if not enabled:
            current_name = ""
            current = {}
            return
        endpoints.append(
            {
                "name": current_name,
                "subdomain": current["subdomain"],
                "namespace": current.get("namespace", ""),
                "service": current.get("service", ""),
                "auth": "protected" if current.get("auth_enabled", "").strip().lower() in {"1", "true", "yes", "on"} else "public",
                "url": f"https://{current['subdomain']}.{domain_name}",
            }
        )
        current_name = ""
        current = {}

    for raw_line in lines:
        stripped = raw_line.strip()
        if not in_ingresses:
            if stripped == "ingresses:":
                in_ingresses = True
            continue

        if re.match(r"^\S", raw_line):
            break
        if not stripped or stripped.startswith("#"):
            continue

        entry_match = re.match(r"^  ([A-Za-z0-9_-]+):\s*$", raw_line)
        if entry_match:
            flush_current()
            current_name = entry_match.group(1)
            current = {}
            continue

        prop_match = re.match(r"^    ([A-Za-z0-9_]+):\s*(.*)$", raw_line)
        if prop_match and current_name:
            key, value = prop_match.groups()
            cleaned = value.strip().strip('"').strip("'")
            if cleaned:
                current[key] = cleaned

    flush_current()
    if not endpoints:
        raise RuntimeError(f"No ingress endpoints were found in {source_path}")
    return endpoints


class NoRedirectHandler(urllib.request.HTTPRedirectHandler):
    def http_error_301(self, req, fp, code, msg, headers):
        return fp

    def http_error_302(self, req, fp, code, msg, headers):
        return fp

    def http_error_303(self, req, fp, code, msg, headers):
        return fp

    def http_error_307(self, req, fp, code, msg, headers):
        return fp

    def http_error_308(self, req, fp, code, msg, headers):
        return fp


def probe_web_status(url: str, timeout_seconds: int = 10) -> int:
    opener = urllib.request.build_opener(NoRedirectHandler)
    request = urllib.request.Request(
        url,
        method="GET",
        headers={
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/135.0.0.0 Safari/537.36"
            ),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
            "Cache-Control": "no-cache",
            "Pragma": "no-cache",
        },
    )
    try:
        with opener.open(request, timeout=timeout_seconds) as response:
            return int(getattr(response, "status", response.getcode()))
    except urllib.error.HTTPError as error:
        return int(error.code)
    except Exception:
        return 0
