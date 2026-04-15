from __future__ import annotations

import json
import re
import urllib.error
import urllib.request
from pathlib import Path
from urllib.parse import urlparse

VALID_AUTH_STRATEGIES = {"public", "edge_forward_auth", "native_oidc", "app_native"}


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
        auth_strategy = current.get("auth_strategy", "").strip()
        if not auth_strategy:
            raise RuntimeError(f"Ingress {current_name} in {source_path} is missing required auth_strategy")
        if auth_strategy not in VALID_AUTH_STRATEGIES:
            raise RuntimeError(f"Ingress {current_name} in {source_path} has invalid auth_strategy {auth_strategy!r}")
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
                "auth": auth_strategy,
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


def probe_web_response(url: str, timeout_seconds: int = 10) -> dict[str, str | int]:
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
            body = response.read(16384).decode("utf-8", errors="replace")
            return {
                "status": int(getattr(response, "status", response.getcode())),
                "location": response.headers.get("Location", ""),
                "body": body,
            }
    except urllib.error.HTTPError as error:
        body = error.read(16384).decode("utf-8", errors="replace")
        return {
            "status": int(error.code),
            "location": error.headers.get("Location", ""),
            "body": body,
        }
    except Exception:
        return {"status": 0, "location": "", "body": ""}


def probe_web_status(url: str, timeout_seconds: int = 10) -> int:
    return int(probe_web_response(url, timeout_seconds)["status"])


def endpoint_verification_success(endpoint: dict[str, str], response: dict[str, str | int], auth_url: str) -> bool:
    status = int(response["status"])
    location = str(response.get("location", "") or "")
    body = str(response.get("body", "") or "")
    auth_strategy = endpoint["auth"]
    if auth_strategy not in VALID_AUTH_STRATEGIES:
        return False
    if auth_strategy == "public":
        return status in {200, 201, 202, 204}

    if auth_strategy == "edge_forward_auth":
        if status == 401:
            return True
        if status not in {301, 302, 303, 307, 308}:
            return False
        if not location:
            return False
        parsed = urlparse(location)
        if not parsed.netloc:
            return not parsed.scheme
        return parsed.netloc == urlparse(auth_url).netloc

    if auth_strategy == "native_oidc":
        if endpoint["name"] == "semaphore":
            return semaphore_login_metadata_success(endpoint["url"])
        if endpoint["name"] == "argocd":
            if status == 200:
                return "Argo CD" in body and '<div id="app"></div>' in body
            if status not in {301, 302, 303, 307, 308} or not location:
                return False
            parsed = urlparse(location)
            if not parsed.netloc:
                return location.startswith("/login")
            return parsed.netloc == urlparse(endpoint["url"]).netloc and parsed.path.startswith("/login")
        if endpoint["name"] == "grafana":
            if status == 200:
                return any(marker in body for marker in ("Welcome to Grafana", "Sign in to Grafana", "Grafana"))
            if status not in {301, 302, 303, 307, 308} or not location:
                return False
            parsed = urlparse(location)
            if not parsed.netloc:
                return location.startswith("/login")
            return parsed.netloc == urlparse(endpoint["url"]).netloc and parsed.path.startswith("/login")
        return False

    if auth_strategy == "app_native":
        if status in {200, 201, 202, 204, 401}:
            return True
        if status not in {301, 302, 303, 307, 308}:
            return False
        if not location:
            return False
        parsed = urlparse(location)
        if not parsed.netloc:
            return not parsed.scheme
        return parsed.netloc == urlparse(endpoint["url"]).netloc

    return False


def semaphore_login_metadata_success(base_url: str) -> bool:
    metadata_url = base_url.rstrip("/") + "/api/auth/login"
    response = probe_web_response(metadata_url)
    if int(response["status"]) != 200:
        return False
    try:
        payload = json.loads(str(response.get("body", "") or "{}"))
    except json.JSONDecodeError:
        return False
    providers = payload.get("oidc_providers") or []
    if not any(provider.get("id") == "authelia" for provider in providers if isinstance(provider, dict)):
        return False
    return payload.get("login_with_password") is False
