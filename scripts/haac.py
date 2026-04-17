#!/usr/bin/env python3
from __future__ import annotations

import argparse
import base64
import hashlib
import json
import os
import platform
import re
import shlex
import shutil
import signal
import socket
import subprocess
import sys
import tarfile
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request
import zipfile
from contextlib import contextmanager
from pathlib import Path, PurePosixPath

from haaclib import endpoints as endpointlib
from haaclib import gitops as gitopslib
from haaclib import gitstate as gitstatelib
from haaclib import secrets as secretlib
from haaclib.authelia import resolve_admin_password_hash
from haaclib.redaction import redact_sensitive_text, secret_values_from_env
from haaclib.sshconfig import ensure_known_hosts_file, resolve_known_hosts_path, resolve_ssh_host_key_mode

ROOT = Path(__file__).resolve().parent.parent
SCRIPTS_DIR = ROOT / "scripts"
K8S_DIR = ROOT / "k8s"
TOOLS_DIR = ROOT / ".tools"
TMP_DIR = ROOT / ".tmp"
LEGACY_TOOLS_BIN_DIR = TOOLS_DIR / "bin"
LEGACY_TOOLS_METADATA_PATH = TOOLS_DIR / "versions.json"
SSH_DIR = ROOT / ".ssh"
SSH_PRIVATE_KEY_PATH = SSH_DIR / "haac_ed25519"
SSH_PUBLIC_KEY_PATH = SSH_DIR / "haac_ed25519.pub"
SEMAPHORE_SSH_PRIVATE_KEY_PATH = SSH_DIR / "haac_semaphore_ed25519"
SEMAPHORE_SSH_PUBLIC_KEY_PATH = SSH_DIR / "haac_semaphore_ed25519.pub"
REPO_DEPLOY_SSH_PRIVATE_KEY_PATH = SSH_DIR / "haac_repo_deploy_ed25519"
REPO_DEPLOY_SSH_PUBLIC_KEY_PATH = SSH_DIR / "haac_repo_deploy_ed25519.pub"
ENV_FILE = ROOT / ".env"
PUB_CERT_PATH = SCRIPTS_DIR / "pub-sealed-secrets.pem"
SECRETS_DIR = K8S_DIR / "charts" / "haac-stack" / "templates" / "secrets"
VALUES_TEMPLATE = K8S_DIR / "charts" / "haac-stack" / "config-templates" / "values.yaml.template"
VALUES_OUTPUT = K8S_DIR / "charts" / "haac-stack" / "values.yaml"
ARGOCD_REPOSERVER_PATCH = K8S_DIR / "platform" / "argocd" / "install-overlay" / "reposerver-patch.yaml"
ARGOCD_OIDC_SECRET_OUTPUT = K8S_DIR / "platform" / "argocd" / "install-overlay" / "argocd-oidc-sealed-secret.yaml"
LITMUS_ADMIN_SECRET_OUTPUT = K8S_DIR / "platform" / "chaos" / "litmus-admin-credentials-sealed-secret.yaml"
HOMEPAGE_WIDGETS_SECRET_OUTPUT = SECRETS_DIR / "homepage-widgets-sealed-secret.yaml"
SEMAPHORE_MAINTENANCE_SSH_SECRET_OUTPUT = SECRETS_DIR / "semaphore-maintenance-ssh-sealed-secret.yaml"
SEMAPHORE_REPO_DEPLOY_SSH_SECRET_OUTPUT = SECRETS_DIR / "semaphore-repo-deploy-ssh-sealed-secret.yaml"
GITOPS_RENDERED_OUTPUTS = (
    K8S_DIR / "argocd-apps.yaml",
    K8S_DIR / "bootstrap" / "root" / "applications" / "platform-root.yaml",
    K8S_DIR / "bootstrap" / "root" / "applications" / "workloads-root.yaml",
    K8S_DIR / "workloads" / "applications" / "haac-stack.yaml",
    K8S_DIR / "platform" / "argocd" / "argocd-app.yaml",
    K8S_DIR / "platform" / "argocd" / "install-overlay" / "argocd-cm.yaml",
    K8S_DIR / "platform" / "applications" / "falco-app.yaml",
    K8S_DIR / "platform" / "falco-ingest-service.yaml",
    K8S_DIR / "platform" / "applications" / "kube-prometheus-stack-app.yaml",
    K8S_DIR / "platform" / "applications" / "semaphore-app.yaml",
)
FALCO_APP_OUTPUT = K8S_DIR / "platform" / "applications" / "falco-app.yaml"
FALCO_INGEST_SERVICE_OUTPUT = K8S_DIR / "platform" / "falco-ingest-service.yaml"
DISABLED_GITOPS_LIST = "apiVersion: v1\nkind: List\nitems: []\n"
HOOKS_DIR = ROOT / ".git" / "hooks"
KUBESEAL_VERSION = "0.36.1"
DEFAULT_WSL_DISTRO = "Debian"
TOFU_VERSION = "1.11.5"
HELM_VERSION = "4.1.3"
KUBECTL_VERSION = "1.35.3"
TASK_VERSION = "3.49.1"
SYSTEM_UPGRADE_CONTROLLER_VERSION = "v0.19.0"
LEGACY_PROXMOX_DOWNLOAD_FILE_ADDRESS = "proxmox_virtual_environment_download_file.debian_container_template"
PROXMOX_DOWNLOAD_FILE_ADDRESS = "proxmox_download_file.debian_container_template"
LEGACY_ARTIFACT_DIRS = (
    ROOT / "output",
    ROOT / ".tmp-falco",
)
LEGACY_ARTIFACT_PATTERNS = (
    ".tmp-*.log",
    "haac-*.log",
    "loop-*.log",
    "master-*.log",
    "worker*-*.log",
)


class HaaCError(RuntimeError):
    pass


UP_TASK_LINE_PATTERN = re.compile(r"^task: \[([^\]]+)\]\s+(.*)$")
UP_TASK_PHASES = {
    "check-env": "Preflight",
    "doctor": "Preflight",
    "sync": "Preflight",
    "setup-hooks": "Preflight",
    "provision-infra": "Infrastructure provisioning",
    "configure-os": "Node configuration",
    "generate-secrets": "GitOps publication",
    "push-changes": "GitOps publication",
    "deploy-argocd": "GitOps publication",
    "wait-for-argocd-sync": "GitOps readiness",
    "sync-cloudflare": "Cloudflare publication",
    "verify-cluster": "Cluster verification",
    "verify-endpoints": "Public URL verification",
}
UP_PHASE_RERUN_GUIDANCE = {
    "Preflight": "No remote bootstrap state changed. Fix the local prerequisite or Git issue, then rerun `task up`.",
    "Infrastructure provisioning": "OpenTofu apply is the normal recovery path. Fix the provisioning issue, then rerun `task up` without destroying converged resources.",
    "Node configuration": "Ansible is expected to reconcile existing hosts. Fix the configuration issue, then rerun `task up`.",
    "GitOps publication": "Earlier phases remain valid. Resolve the Git or publication issue, then rerun `task up` to continue reconciliation.",
    "GitOps readiness": "Earlier phases are already convergent. Fix the failing readiness gate, then rerun `task up`.",
    "Cloudflare publication": "Cluster-side phases stay converged. Fix the Cloudflare issue, then rerun `task up`.",
    "Cluster verification": "Provisioning and publication phases already completed. Fix the cluster-health issue, then rerun `task up`.",
    "Public URL verification": "Earlier phases already converged. Fix the ingress, DNS, TLS, or auth issue, then rerun `task up`.",
}


def load_env_file(path: Path = ENV_FILE) -> dict[str, str]:
    data: dict[str, str] = {}
    if not path.exists():
        return data

    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        value = value.strip()
        if value.startswith(("'", '"')) and value.endswith(("'", '"')) and len(value) >= 2:
            value = value[1:-1]
        data[key.strip()] = value
    return data


def merged_env() -> dict[str, str]:
    env = load_env_file()
    merged = os.environ.copy()
    for key, value in env.items():
        merged.setdefault(key, value)
    if not merged.get("PROXMOX_HOST_PASSWORD") and merged.get("LXC_PASSWORD"):
        merged["PROXMOX_HOST_PASSWORD"] = merged["LXC_PASSWORD"]
    merged.setdefault("HAAC_FALCO_INGEST_NODEPORT", "32081")
    if merged.get("GRAFANA_OIDC_SECRET"):
        merged.setdefault(
            "GRAFANA_OIDC_SECRET_SHA256",
            hashlib.sha256(merged["GRAFANA_OIDC_SECRET"].encode("utf-8")).hexdigest(),
        )
    merged.setdefault("LITMUS_ADMIN_USERNAME", "admin")
    if merged.get("AUTHELIA_ADMIN_PASSWORD"):
        merged.setdefault("LITMUS_ADMIN_PASSWORD", merged["AUTHELIA_ADMIN_PASSWORD"])
    return merged


def proxmox_node_name(env: dict[str, str]) -> str:
    return env.get("MASTER_TARGET_NODE", "pve").strip() or "pve"


def proxmox_access_host(env: dict[str, str]) -> str:
    access_host = env.get("PROXMOX_ACCESS_HOST", "").strip()
    return access_host or proxmox_node_name(env)


def maintenance_user(env: dict[str, str]) -> str:
    return env.get("HAAC_MAINTENANCE_USER", "haac-maint").strip() or "haac-maint"


def repo_url_requires_ssh_auth(repo_url: str) -> bool:
    lowered = repo_url.strip().lower()
    return lowered.startswith("git@") or lowered.startswith("ssh://")


def local_kubeconfig_path() -> Path:
    override = os.environ.get("HAAC_KUBECONFIG_PATH")
    if override:
        return Path(override)
    return Path.home() / ".kube" / "haac-k3s.yaml"


def ensure_parent(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def ensure_tmp_dir(*segments: str) -> Path:
    path = TMP_DIR.joinpath(*segments)
    path.mkdir(parents=True, exist_ok=True)
    return path


def is_windows() -> bool:
    return os.name == "nt"


def binary_name(name: str) -> str:
    return binary_name_for_platform(name, host_platform())


def binary_name_for_platform(name: str, platform_name: str) -> str:
    return f"{name}.exe" if platform_name == "windows" else name


def platform_tools_dir(platform_name: str, arch: str) -> Path:
    return TOOLS_DIR / f"{platform_name}-{arch}"


def platform_tools_bin_dir(platform_name: str, arch: str) -> Path:
    return platform_tools_dir(platform_name, arch) / "bin"


def platform_tools_metadata_path(platform_name: str, arch: str) -> Path:
    return platform_tools_dir(platform_name, arch) / "versions.json"


def local_binary_path(name: str, platform_name: str | None = None, arch: str | None = None) -> Path:
    platform_name = platform_name or host_platform()
    arch = arch or host_arch()
    return platform_tools_bin_dir(platform_name, arch) / binary_name_for_platform(name, platform_name)


def legacy_local_binary_path(name: str) -> Path:
    return LEGACY_TOOLS_BIN_DIR / binary_name(name)


def tool_location(name: str) -> str | None:
    local_path = local_binary_path(name)
    if local_path.exists():
        return str(local_path)
    legacy_path = legacy_local_binary_path(name)
    if legacy_path.exists():
        return str(legacy_path)
    found = shutil.which(name)
    if found:
        return found
    return None


def resolved_binary(name: str) -> str:
    return tool_location(name) or name


def redaction_values(env: dict[str, str] | None = None) -> list[str]:
    return secret_values_from_env(env or merged_env())


def redact_text(text: str, env: dict[str, str] | None = None) -> str:
    return redact_sensitive_text(text, redaction_values(env))


def known_hosts_path(env: dict[str, str] | None = None) -> Path:
    return ensure_known_hosts_file(resolve_known_hosts_path(ROOT, env or merged_env()))


def ssh_host_key_checking_mode(env: dict[str, str] | None = None) -> str:
    return resolve_ssh_host_key_mode(env or merged_env())


def ssh_common_options(
    *,
    connect_timeout: int = 5,
    env: dict[str, str] | None = None,
    known_hosts_file: str | None = None,
) -> list[str]:
    working_env = env or merged_env()
    known_hosts_file = known_hosts_file or str(known_hosts_path(working_env))
    return [
        "-o",
        f"StrictHostKeyChecking={ssh_host_key_checking_mode(working_env)}",
        "-o",
        f"UserKnownHostsFile={known_hosts_file}",
        "-o",
        "BatchMode=yes",
        "-o",
        f"ConnectTimeout={connect_timeout}",
        "-o",
        "ConnectionAttempts=1",
    ]


def proxmox_ssh_base_command(host: str, *, connect_timeout: int = 5) -> list[str]:
    env = merged_env()
    command = [
        "ssh",
        *ssh_common_options(connect_timeout=connect_timeout, env=env),
        "-o",
        "IdentitiesOnly=yes",
    ]
    if SSH_PRIVATE_KEY_PATH.exists():
        command.extend(["-i", str(SSH_PRIVATE_KEY_PATH)])
    command.append(f"root@{host}")
    return command


def proxmox_ssh_command(host: str, remote_command: str, *, connect_timeout: int = 5) -> list[str]:
    if is_windows():
        env = merged_env()
        ssh_key_wsl = ensure_wsl_ssh_keypair(env)
        known_hosts_wsl = ensure_wsl_known_hosts(env)
        ssh_command = [
            "ssh",
            *ssh_common_options(connect_timeout=connect_timeout, env=env, known_hosts_file=known_hosts_wsl),
            "-o",
            "IdentitiesOnly=yes",
            "-i",
            ssh_key_wsl,
            f"root@{host}",
            remote_command,
        ]
        return wsl_command(
            "bash",
            "-lc",
            "exec " + " ".join(shlex.quote(part) for part in ssh_command),
            distro=wsl_distro(env),
        )
    return [*proxmox_ssh_base_command(host, connect_timeout=connect_timeout), remote_command]


def run_proxmox_ssh(
    host: str,
    remote_command: str,
    *,
    connect_timeout: int = 5,
    check: bool = True,
    capture_output: bool = False,
) -> subprocess.CompletedProcess[str]:
    env = merged_env()
    try:
        return run(
            proxmox_ssh_command(host, remote_command, connect_timeout=connect_timeout),
            env=env,
            check=check,
            capture_output=capture_output,
        )
    finally:
        if is_windows():
            cleanup_wsl_runtime(env)


def run_proxmox_ssh_stdout(host: str, remote_command: str, *, connect_timeout: int = 5, check: bool = True) -> str:
    return run_proxmox_ssh(
        host,
        remote_command,
        connect_timeout=connect_timeout,
        check=check,
        capture_output=True,
    ).stdout.strip()


def proxmox_tunnel_command(
    host: str,
    *,
    master_ip: str,
    local_port: int = 6443,
    remote_port: int = 6443,
    connect_timeout: int = 10,
) -> list[str]:
    if is_windows():
        env = merged_env()
        ssh_key_wsl = ensure_wsl_ssh_keypair(env)
        known_hosts_wsl = ensure_wsl_known_hosts(env)
        ssh_command = [
            "ssh",
            *ssh_common_options(connect_timeout=connect_timeout, env=env, known_hosts_file=known_hosts_wsl),
            "-o",
            "IdentitiesOnly=yes",
            "-i",
            ssh_key_wsl,
            "-o",
            "ExitOnForwardFailure=yes",
            "-o",
            "ServerAliveInterval=30",
            "-o",
            "ServerAliveCountMax=3",
            "-N",
            "-L",
            f"{local_port}:{master_ip}:{remote_port}",
            f"root@{host}",
        ]
        return wsl_command(
            "bash",
            "-lc",
            "exec " + " ".join(shlex.quote(part) for part in ssh_command),
            distro=wsl_distro(env),
        )
    return [
        *proxmox_ssh_base_command(host, connect_timeout=connect_timeout)[:-1],
        "-o",
        "ExitOnForwardFailure=yes",
        "-o",
        "ServerAliveInterval=30",
        "-o",
        "ServerAliveCountMax=3",
        "-N",
        "-L",
        f"{local_port}:{master_ip}:{remote_port}",
        proxmox_ssh_base_command(host, connect_timeout=connect_timeout)[-1],
    ]


def host_platform() -> str:
    system_name = platform.system().lower()
    if system_name.startswith("msys") or system_name.startswith("cygwin"):
        return "windows"
    if system_name.startswith("windows"):
        return "windows"
    if system_name.startswith("darwin"):
        return "darwin"
    if system_name.startswith("linux"):
        return "linux"
    raise HaaCError(f"Unsupported platform for local tool bootstrap: {system_name}")


def host_arch() -> str:
    machine = platform.machine().lower()
    arch_map = {
        "x86_64": "amd64",
        "amd64": "amd64",
        "arm64": "arm64",
        "aarch64": "arm64",
    }
    arch = arch_map.get(machine)
    if not arch:
        raise HaaCError(f"Unsupported architecture for local tool bootstrap: {machine}")
    return arch


def bootstrappable_tools() -> set[str]:
    return {"tofu", "helm", "kubectl", "kubeseal", "task"}


def command_label(command: list[str]) -> str:
    return " ".join(shlex.quote(part) for part in command)


def should_run_tool_in_wsl(command: list[str]) -> bool:
    if not is_windows() or not command or shutil.which("wsl") is None:
        return False
    return Path(command[0]).stem.lower() in {"kubectl", "kubeseal", "helm"}


def maybe_resolve_local_path(token: str, cwd: Path) -> Path | None:
    if not token or token == "-" or token.startswith("http://") or token.startswith("https://"):
        return None
    if re.match(r"^[A-Za-z]:[\\/]", token):
        candidate = Path(token)
        return candidate if candidate.exists() else None
    candidate = Path(token)
    if candidate.is_absolute():
        return candidate if candidate.exists() else None
    resolved = (cwd / candidate).resolve()
    return resolved if resolved.exists() else None


def convert_wsl_tool_arg(token: str, cwd: Path, env: dict[str, str]) -> str:
    for prefix in ("--kubeconfig=", "--cert=", "--patch-file=", "--filename=", "--ca-file=", "--key="):
        if token.startswith(prefix):
            resolved = maybe_resolve_local_path(token[len(prefix) :], cwd)
            if resolved is not None:
                return prefix + to_posix_wsl_path(resolved, env)
            return token

    if token.startswith("--from-file="):
        head, _, tail = token.rpartition("=")
        resolved = maybe_resolve_local_path(tail, cwd)
        if resolved is not None:
            return f"{head}={to_posix_wsl_path(resolved, env)}"
        return token

    resolved = maybe_resolve_local_path(token, cwd)
    if resolved is not None:
        return to_posix_wsl_path(resolved, env)
    return token


def wrap_wsl_tool_command(command: list[str], cwd: Path, env: dict[str, str] | None) -> list[str]:
    if not should_run_tool_in_wsl(command):
        return command

    working_env = env or merged_env()
    tool_name = Path(command[0]).stem.lower()
    linux_binary = ensure_local_cli_tool(tool_name, "linux", wsl_arch(working_env))
    linux_binary_wsl = to_posix_wsl_path(linux_binary, working_env)
    cwd_wsl = to_posix_wsl_path(cwd, working_env)
    converted_args = [convert_wsl_tool_arg(arg, cwd, working_env) for arg in command[1:]]
    shell_command = "cd " + shlex.quote(cwd_wsl) + " && exec " + " ".join(
        shlex.quote(part) for part in [linux_binary_wsl, *converted_args]
    )
    return wsl_command("bash", "-lc", shell_command, distro=wsl_distro(working_env))


def run(
    command: list[str],
    *,
    cwd: Path = ROOT,
    env: dict[str, str] | None = None,
    check: bool = True,
    capture_output: bool = False,
    input_text: str | None = None,
    input_bytes: bytes | None = None,
) -> subprocess.CompletedProcess[str]:
    command = wrap_wsl_tool_command(command, cwd, env)
    working_env = env or merged_env()
    text_mode = input_bytes is None
    completed = subprocess.run(
        command,
        cwd=str(cwd),
        env=env,
        text=text_mode,
        encoding="utf-8" if text_mode else None,
        errors="replace" if text_mode else None,
        input=input_text if text_mode else input_bytes,
        capture_output=capture_output,
        check=False,
    )
    if check and completed.returncode != 0:
        stderr = completed.stderr.decode("utf-8", errors="replace").strip() if input_bytes is not None and completed.stderr else completed.stderr.strip() if completed.stderr else ""
        stdout = completed.stdout.decode("utf-8", errors="replace").strip() if input_bytes is not None and completed.stdout else completed.stdout.strip() if completed.stdout else ""
        detail = stderr or stdout or f"exit code {completed.returncode}"
        raise HaaCError(f"Command failed: {redact_text(command_label(command), working_env)}\n{redact_text(detail, working_env)}")
    return completed


def run_stdout(
    command: list[str],
    *,
    cwd: Path = ROOT,
    env: dict[str, str] | None = None,
    check: bool = True,
    input_text: str | None = None,
) -> str:
    return run(command, cwd=cwd, env=env, capture_output=True, check=check, input_text=input_text).stdout.strip()


def require_env(keys: list[str], env: dict[str, str]) -> None:
    missing = [key for key in keys if not env.get(key)]
    if missing:
        raise HaaCError(f"Missing required environment variables: {', '.join(missing)}")


def gitops_revision(env: dict[str, str]) -> str:
    revision = env.get("GITOPS_REPO_REVISION", "").strip()
    if not revision:
        raise HaaCError("Missing required environment variable: GITOPS_REPO_REVISION")
    return revision


def gitops_repo_url(env: dict[str, str]) -> str:
    repo_url = env.get("GITOPS_REPO_URL", "").strip()
    if not repo_url:
        raise HaaCError("Missing required environment variable: GITOPS_REPO_URL")
    return repo_url


def ensure_tcp_endpoint(
    host: str,
    port: int,
    *,
    label: str,
    timeout_seconds: int = 5,
    hint: str | None = None,
) -> None:
    try:
        with socket.create_connection((host, port), timeout=timeout_seconds):
            return
    except socket.gaierror as exc:
        guidance = hint or "Update the configured host or local DNS/hosts before running `task up`."
        raise HaaCError(
            f"{label} target '{host}' is not resolvable from this workstation. {guidance}\n{exc}"
        ) from exc
    except OSError as exc:
        raise HaaCError(
            f"{label} is not reachable at {host}:{port}. Connect to the required network or fix access before rerunning `task up`.\n{exc}"
        ) from exc


def stage_git_paths(paths: list[str] | None = None) -> None:
    if paths:
        run(["git", "add", "-A", "--", *paths])
        return
    run(["git", "add", "-A"])


def git_has_staged_changes() -> bool:
    return run(["git", "diff", "--cached", "--quiet"], check=False).returncode != 0


def checkpoint_git_changes(commit_message: str, *, empty_message: str, paths: list[str] | None = None) -> bool:
    stage_git_paths(paths)
    if not git_has_staged_changes():
        print(empty_message)
        return False

    committed = run(["git", "commit", "-m", commit_message, "--no-verify"], check=False, capture_output=True)
    require_success(committed, f"Git checkpoint failed for '{commit_message}'")
    print(f"[ok] Git checkpoint commit: {run_stdout(['git', 'rev-parse', 'HEAD'])}")
    return True


def bootstrap_recovery_summary(
    *,
    failing_phase: str,
    last_verified_phase: str,
    rerun_guidance: str,
    detail: str,
) -> str:
    return (
        f"{detail}\n"
        f"Bootstrap phase: {failing_phase}\n"
        f"Last verified phase: {last_verified_phase}\n"
        f"Full rerun guidance: {rerun_guidance}"
    )


def infer_up_phase(task_name: str, command_text: str) -> str | None:
    phase = UP_TASK_PHASES.get(task_name)
    if phase:
        return phase
    if task_name == "up" and " run-tofu " in f" {command_text} ":
        return "Infrastructure provisioning"
    return None


def emit_up_failure_summary(output_lines: list[str]) -> None:
    phases: list[str] = []
    for line in output_lines:
        match = UP_TASK_LINE_PATTERN.match(line)
        if not match:
            continue
        phase = infer_up_phase(match.group(1), match.group(2))
        if phase and (not phases or phases[-1] != phase):
            phases.append(phase)

    if not phases:
        return

    failing_phase = phases[-1]
    last_verified_phase = phases[-2] if len(phases) >= 2 else "None"
    rerun_guidance = UP_PHASE_RERUN_GUIDANCE.get(
        failing_phase,
        "Fix the reported issue, then rerun `task up` if earlier phases are already aligned.",
    )
    print(f"[recovery] Failing phase: {failing_phase}", file=sys.stderr)
    print(f"[recovery] Last verified phase: {last_verified_phase}", file=sys.stderr)
    print(f"[recovery] Full rerun guidance: {rerun_guidance}", file=sys.stderr)


def run_task_with_output(task_binary: str, task_args: list[str], env: dict[str, str]) -> tuple[int, list[str]]:
    process = subprocess.Popen(
        [task_binary, *task_args],
        cwd=str(ROOT),
        env=env,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        bufsize=1,
    )
    if process.stdout is None:
        return process.wait(), []

    output_lines: list[str] = []
    for line in process.stdout:
        print(line, end="")
        output_lines.append(line.rstrip("\n"))
    return process.wait(), output_lines


def wsl_command(*args: str, distro: str | None = None, user: str | None = None) -> list[str]:
    command = ["wsl"]
    if distro:
        command.extend(["-d", distro])
    if user:
        command.extend(["-u", user])
    command.append("--")
    command.extend(args)
    return command


def wsl_distro(env: dict[str, str]) -> str:
    return env.get("HAAC_WSL_DISTRO", DEFAULT_WSL_DISTRO)


def to_posix_wsl_path(path: Path, env: dict[str, str]) -> str:
    native_path = str(path)
    if is_windows():
        native_path = native_path.replace("\\", "/")
    return run_stdout(wsl_command("wslpath", "-a", native_path, distro=wsl_distro(env)))


def wsl_home_dir(env: dict[str, str]) -> str:
    return run_stdout(wsl_command("bash", "-lc", "printf %s \"$HOME\"", distro=wsl_distro(env)))


def wsl_runtime_dir(env: dict[str, str]) -> str:
    runtime_root = env.get("HAAC_WSL_RUNTIME_ROOT", "/tmp/haac-runtime").strip() or "/tmp/haac-runtime"
    return f"{runtime_root.rstrip('/')}/{wsl_distro(env)}"


def ensure_wsl_runtime_dir(env: dict[str, str]) -> str:
    runtime_dir_wsl = wsl_runtime_dir(env)
    run(
        wsl_command(
            "bash",
            "-lc",
            f"mkdir -p {shlex.quote(runtime_dir_wsl)} && chmod 700 {shlex.quote(runtime_dir_wsl)}",
            distro=wsl_distro(env),
        )
    )
    return runtime_dir_wsl


def ensure_wsl_ssh_keypair(env: dict[str, str]) -> str:
    if not SSH_PRIVATE_KEY_PATH.exists() or not SSH_PUBLIC_KEY_PATH.exists():
        raise HaaCError(f"Repo SSH keypair not found: {SSH_PRIVATE_KEY_PATH}")

    runtime_dir_wsl = ensure_wsl_runtime_dir(env)
    private_key_wsl = f"{runtime_dir_wsl}/haac_ed25519"
    private_key_source_wsl = to_posix_wsl_path(SSH_PRIVATE_KEY_PATH, env)
    public_key_source_wsl = to_posix_wsl_path(SSH_PUBLIC_KEY_PATH, env)
    command = (
        f"rm -f {shlex.quote(private_key_wsl)} {shlex.quote(private_key_wsl)}.pub && "
        f"cp -f {shlex.quote(private_key_source_wsl)} {shlex.quote(private_key_wsl)} && "
        f"cp -f {shlex.quote(public_key_source_wsl)} {shlex.quote(private_key_wsl)}.pub && "
        f"chmod 600 {shlex.quote(private_key_wsl)} && chmod 644 {shlex.quote(private_key_wsl)}.pub"
    )
    run(wsl_command("bash", "-lc", command, distro=wsl_distro(env)))
    return private_key_wsl


def ensure_wsl_known_hosts(env: dict[str, str]) -> str:
    local_known_hosts = known_hosts_path(env)
    runtime_dir_wsl = ensure_wsl_runtime_dir(env)
    known_hosts_wsl = f"{runtime_dir_wsl}/haac_known_hosts"
    local_known_hosts_wsl = to_posix_wsl_path(local_known_hosts, env)
    command = (
        f"rm -f {shlex.quote(known_hosts_wsl)} && "
        f"cp -f {shlex.quote(local_known_hosts_wsl)} {shlex.quote(known_hosts_wsl)} && "
        f"chmod 600 {shlex.quote(known_hosts_wsl)}"
    )
    run(wsl_command("bash", "-lc", command, distro=wsl_distro(env)))
    return known_hosts_wsl


def sync_wsl_known_hosts_back(env: dict[str, str], known_hosts_wsl: str) -> None:
    local_known_hosts = known_hosts_path(env)
    ensure_parent(local_known_hosts)
    local_known_hosts_wsl = to_posix_wsl_path(local_known_hosts, env)
    command = (
        "if [ -f {src} ]; then "
        "cp {src} {dst} && chmod 600 {dst}; "
        "fi"
    ).format(src=shlex.quote(known_hosts_wsl), dst=shlex.quote(local_known_hosts_wsl))
    run(wsl_command("bash", "-lc", command, distro=wsl_distro(env)), check=False)


def cleanup_wsl_runtime(env: dict[str, str]) -> None:
    runtime_dir_wsl = wsl_runtime_dir(env)
    if runtime_dir_wsl:
        run(
            wsl_command("bash", "-lc", f"rm -rf {shlex.quote(runtime_dir_wsl)}", distro=wsl_distro(env)),
            check=False,
        )


def run_ansible_wsl(inventory: Path, playbook: Path, extra_args: list[str], env: dict[str, str]) -> None:
    if shutil.which("wsl") is None:
        raise HaaCError(
            "Ansible on Windows requires WSL. Install WSL and make ansible-playbook available inside it."
        )

    repo_wsl = to_posix_wsl_path(ROOT, env)
    inventory_wsl = to_posix_wsl_path(inventory, env)
    playbook_wsl = to_posix_wsl_path(playbook, env)
    kubeconfig_wsl = to_posix_wsl_path(local_kubeconfig_path(), env)
    kube_dir_wsl = str(PurePosixPath(kubeconfig_wsl).parent)
    ssh_key_wsl = ensure_wsl_ssh_keypair(env)
    known_hosts_wsl = ensure_wsl_known_hosts(env)

    env_exports = {
        key: env[key].strip()
        for key in (
            "PROXMOX_HOST_PASSWORD",
            "LXC_PASSWORD",
            "NAS_PATH",
            "NAS_SHARE_NAME",
            "SMB_USER",
            "SMB_PASSWORD",
            "STORAGE_UID",
            "STORAGE_GID",
            "HAAC_ENABLE_FALCO",
            "LXC_K3S_COMPAT_MODE",
            "LXC_ENABLE_GPU_PASSTHROUGH",
            "LXC_ENABLE_TUN",
            "LXC_ENABLE_EBPF_MOUNTS",
        )
        if key in env and env[key]
    }
    env_exports["HAAC_KUBECONFIG_PATH"] = kubeconfig_wsl
    env_exports["HAAC_SSH_PRIVATE_KEY_PATH"] = ssh_key_wsl
    env_exports["HAAC_SSH_KNOWN_HOSTS_PATH"] = known_hosts_wsl
    env_exports["HAAC_SSH_HOST_KEY_CHECKING"] = ssh_host_key_checking_mode(env)
    env_exports["HAAC_PROXMOX_ACCESS_HOST"] = proxmox_access_host(env)

    args = " ".join(shlex.quote(arg) for arg in extra_args)
    script_lines = [f"export {key}={shlex.quote(value)}" for key, value in env_exports.items()]
    script_lines.extend(
        [
            f"cd {shlex.quote(repo_wsl)}",
            f"mkdir -p {shlex.quote(kube_dir_wsl)}",
            f"ansible-playbook {args} -i {shlex.quote(inventory_wsl)} {shlex.quote(playbook_wsl)}",
        ]
    )
    script_bytes = ("\n".join(script_lines) + "\n").encode("utf-8")
    try:
        run(wsl_command("bash", "-se", distro=wsl_distro(env)), input_bytes=script_bytes)
    finally:
        sync_wsl_known_hosts_back(env, known_hosts_wsl)
        cleanup_wsl_runtime(env)


def allocate_local_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def rewrite_kubeconfig_server(kubeconfig: Path, server: str = "https://127.0.0.1:6443") -> None:
    if not kubeconfig.exists():
        raise HaaCError(f"Kubeconfig not found: {kubeconfig}")

    content = kubeconfig.read_text(encoding="utf-8")
    updated = re.sub(r"(^\s*server:\s*)https://[^\s]+(\s*$)", rf"\1{server}\2", content, flags=re.MULTILINE)
    kubeconfig.write_text(updated, encoding="utf-8")


def wait_for_k8s_api(kubeconfig: Path, kubectl: str, timeout_seconds: int = 120, interval_seconds: int = 2) -> None:
    deadline = time.time() + timeout_seconds
    while time.time() < deadline:
        completed = run(
            [kubectl, "--kubeconfig", str(kubeconfig), "get", "--raw", "/healthz"],
            check=False,
            capture_output=True,
        )
        if completed.returncode == 0:
            return
        time.sleep(interval_seconds)
    raise HaaCError("K3s API did not become ready before timeout")


def session_kubeconfig_copy(source: Path, server: str) -> tuple[Path, Path]:
    if not source.exists():
        raise HaaCError(f"Kubeconfig not found: {source}")

    session_dir = Path(tempfile.mkdtemp(prefix="haac-kubeconfig-", dir=ensure_tmp_dir("kube-sessions")))
    session_kubeconfig = session_dir / source.name
    shutil.copy2(source, session_kubeconfig)
    rewrite_kubeconfig_server(session_kubeconfig, server)
    return session_dir, session_kubeconfig


def tunnel_failure_detail(process: subprocess.Popen[str], command: list[str]) -> str:
    stderr = process.stderr.read().strip() if process.stderr else ""
    return stderr or command_label(command)


@contextmanager
def ssh_tunnel(proxmox_host: str, master_ip: str, local_port: int | None = None, remote_port: int = 6443):
    resolved_local_port = local_port or allocate_local_port()
    env = merged_env()
    last_error = ""
    last_command: list[str] | None = None
    for attempt in range(1, 4):
        # On Windows the WSL runtime-backed key material is recreated per attempt.
        # Rebuild the command after any previous cleanup so retries do not reuse stale paths.
        command = proxmox_tunnel_command(
            proxmox_host,
            master_ip=master_ip,
            local_port=resolved_local_port,
            remote_port=remote_port,
            connect_timeout=10,
        )
        last_command = command
        process = subprocess.Popen(
            command,
            cwd=str(ROOT),
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
            text=True,
            creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if is_windows() else 0,
        )
        try:
            time.sleep(2)
            if process.poll() is not None:
                last_error = tunnel_failure_detail(process, command)
                if attempt < 3:
                    print(f"[warn] SSH tunnel start attempt {attempt}/3 failed: {last_error}. Retrying...")
                    time.sleep(attempt)
                    continue
                raise HaaCError(f"SSH tunnel failed to start: {last_error}")
            yield resolved_local_port
            return
        finally:
            if process.poll() is None:
                if is_windows():
                    subprocess.run(["taskkill", "/PID", str(process.pid), "/T", "/F"], check=False, capture_output=True)
                else:
                    process.send_signal(signal.SIGTERM)
                    try:
                        process.wait(timeout=5)
                    except subprocess.TimeoutExpired:
                        process.kill()
            if is_windows():
                cleanup_wsl_runtime(env)
    raise HaaCError(f"SSH tunnel failed to start: {last_error or command_label(last_command or [])}")


@contextmanager
def cluster_session(proxmox_host: str, master_ip: str, kubeconfig: Path, kubectl: str):
    ensure_parent(kubeconfig)
    with ssh_tunnel(proxmox_host, master_ip) as local_port:
        session_dir, session_kubeconfig = session_kubeconfig_copy(kubeconfig, f"https://127.0.0.1:{local_port}")
        try:
            wait_for_k8s_api(session_kubeconfig, kubectl)
            yield session_kubeconfig
        finally:
            shutil.rmtree(session_dir, ignore_errors=True)


def cleanup_disabled_falco(kubectl: str, kubeconfig: Path) -> None:
    run(
        [
            kubectl,
            "--kubeconfig",
            str(kubeconfig),
            "delete",
            "application",
            "falco",
            "-n",
            "argocd",
            "--ignore-not-found=true",
        ],
        check=False,
        capture_output=True,
    )
    completed = run(
        [
            kubectl,
            "--kubeconfig",
            str(kubeconfig),
            "delete",
            "all,cm,secret,sa,role,rolebinding,pvc",
            "-n",
            "security",
            "-l",
            "app.kubernetes.io/instance=falco",
            "--ignore-not-found=true",
        ],
        check=False,
        capture_output=True,
    )
    if completed.returncode == 0 and completed.stdout.strip():
        print("[ok] Removed disabled Falco release resources from namespace security")


def cleanup_disabled_platform_apps(kubectl: str, kubeconfig: Path, env: dict[str, str]) -> None:
    if not gitopslib.falco_enabled(env):
        cleanup_disabled_falco(kubectl, kubeconfig)


def cleanup_falco_legacy_ui_storage(kubectl: str, kubeconfig: Path, env: dict[str, str]) -> None:
    if not gitopslib.falco_enabled(env):
        return
    if not FALCO_APP_OUTPUT.exists():
        return

    falco_config = FALCO_APP_OUTPUT.read_text(encoding="utf-8")
    if "storageEnabled: false" not in falco_config:
        return

    existing = run(
        [
            kubectl,
            "--kubeconfig",
            str(kubeconfig),
            "get",
            "statefulset,pvc,pod",
            "-n",
            "security",
            "-o",
            "name",
        ],
        check=False,
        capture_output=True,
    )
    if existing.returncode != 0:
        return

    stale_resources: list[str] = []
    for resource_name in (existing.stdout or "").splitlines():
        resource_name = resource_name.strip()
        if not resource_name:
            continue
        kind, _, name = resource_name.partition("/")
        if kind.startswith("statefulset") and name == "falco-falcosidekick-ui-redis":
            stale_resources.append(resource_name)
            continue
        if kind == "persistentvolumeclaim" and name.startswith("falco-falcosidekick-ui-redis-data-"):
            stale_resources.append(resource_name)
            continue
        if kind == "pod" and (
            name.startswith("falco-falcosidekick-ui-redis-")
            or name.startswith("falco-falcosidekick-ui-")
        ):
            stale_resources.append(resource_name)

    if not stale_resources:
        return

    deleted = run(
        [
            kubectl,
            "--kubeconfig",
            str(kubeconfig),
            "delete",
            "-n",
            "security",
            "--ignore-not-found=true",
            "--wait=false",
            *stale_resources,
        ],
        check=False,
        capture_output=True,
    )
    if deleted.returncode == 0:
        deadline = time.time() + 180
        while time.time() < deadline:
            remaining = run(
                [
                    kubectl,
                    "--kubeconfig",
                    str(kubeconfig),
                    "get",
                    "statefulset,pvc,pod",
                    "-n",
                    "security",
                    "-o",
                    "name",
                ],
                check=False,
                capture_output=True,
            )
            if remaining.returncode != 0:
                break
            live_resources = {line.strip() for line in (remaining.stdout or "").splitlines() if line.strip()}
            if not any(resource in live_resources for resource in stale_resources):
                break
            time.sleep(3)
        print("[ok] Removed legacy Falco UI Redis resources to converge on the stateless Web UI profile")


def render_env_placeholders(content: str, env: dict[str, str]) -> str:
    return gitopslib.render_env_placeholders(content, env)


def render_values_file(env: dict[str, str]) -> None:
    gitopslib.render_values_file(VALUES_TEMPLATE, VALUES_OUTPUT, env)


def gitops_template_path(output_path: Path) -> Path:
    return gitopslib.gitops_template_path(output_path)


def render_gitops_manifests(env: dict[str, str]) -> None:
    try:
        gitopslib.render_gitops_manifests(
            env=env,
            outputs=GITOPS_RENDERED_OUTPUTS,
            falco_outputs=(FALCO_APP_OUTPUT, FALCO_INGEST_SERVICE_OUTPUT),
            disabled_gitops_list=DISABLED_GITOPS_LIST,
        )
    except RuntimeError as exc:
        raise HaaCError(str(exc)) from exc


def tool_version(env: dict[str, str], env_key: str, default: str) -> str:
    return env.get(env_key, default).strip() or default


def read_tool_metadata(platform_name: str | None = None, arch: str | None = None) -> dict[str, str]:
    platform_name = platform_name or host_platform()
    arch = arch or host_arch()
    metadata_path = platform_tools_metadata_path(platform_name, arch)
    if metadata_path.exists():
        try:
            content = json.loads(metadata_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return {}
        if not isinstance(content, dict):
            return {}
        return {str(key): str(value) for key, value in content.items()}

    if platform_name == host_platform() and arch == host_arch() and LEGACY_TOOLS_METADATA_PATH.exists():
        try:
            content = json.loads(LEGACY_TOOLS_METADATA_PATH.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return {}
        if not isinstance(content, dict):
            return {}
        return {str(key): str(value) for key, value in content.items()}

    return {}


def write_tool_metadata(metadata: dict[str, str], platform_name: str | None = None, arch: str | None = None) -> None:
    platform_name = platform_name or host_platform()
    arch = arch or host_arch()
    metadata_path = platform_tools_metadata_path(platform_name, arch)
    metadata_path.parent.mkdir(parents=True, exist_ok=True)
    metadata_path.write_text(json.dumps(metadata, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def requested_tool_version(name: str, env: dict[str, str]) -> str:
    version_map = {
        "tofu": tool_version(env, "HAAC_TOFU_VERSION", TOFU_VERSION),
        "helm": tool_version(env, "HAAC_HELM_VERSION", HELM_VERSION),
        "kubectl": tool_version(env, "HAAC_KUBECTL_VERSION", KUBECTL_VERSION),
        "kubeseal": tool_version(env, "HAAC_KUBESEAL_VERSION", KUBESEAL_VERSION),
        "task": tool_version(env, "HAAC_TASK_VERSION", TASK_VERSION),
    }
    return version_map[name]


def ensure_executable(destination: Path, platform_name: str) -> None:
    if platform_name != "windows":
        destination.chmod(0o755)


def install_direct_binary(url: str, destination: Path, platform_name: str) -> str:
    destination.parent.mkdir(parents=True, exist_ok=True)
    with urllib.request.urlopen(url) as response:
        destination.write_bytes(response.read())
    ensure_executable(destination, platform_name)
    return str(destination)


def install_zip_binary(url: str, inner_path: str, destination: Path, platform_name: str) -> str:
    destination.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(delete=False, suffix=".zip") as temp_file:
        temp_path = Path(temp_file.name)
        with urllib.request.urlopen(url) as response:
            temp_file.write(response.read())

    try:
        with zipfile.ZipFile(temp_path) as archive:
            with archive.open(inner_path) as extracted:
                destination.write_bytes(extracted.read())
    finally:
        temp_path.unlink(missing_ok=True)

    ensure_executable(destination, platform_name)
    return str(destination)


def install_targz_binary(url: str, inner_path: str, destination: Path, platform_name: str) -> str:
    destination.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(delete=False, suffix=".tar.gz") as temp_file:
        temp_path = Path(temp_file.name)
        with urllib.request.urlopen(url) as response:
            temp_file.write(response.read())

    try:
        with tarfile.open(temp_path, "r:gz") as archive:
            extracted = archive.extractfile(inner_path)
            if extracted is None:
                raise HaaCError(f"Archive entry not found: {inner_path}")
            destination.write_bytes(extracted.read())
    finally:
        temp_path.unlink(missing_ok=True)

    ensure_executable(destination, platform_name)
    return str(destination)


def ensure_local_cli_tool(name: str, platform_name: str | None = None, arch: str | None = None) -> str:
    env = merged_env()
    platform_name = platform_name or host_platform()
    arch = arch or host_arch()
    destination = local_binary_path(name, platform_name, arch)
    metadata = read_tool_metadata(platform_name, arch)
    requested_version = requested_tool_version(name, env)
    if destination.exists() and metadata.get(name) == requested_version:
        return str(destination)

    if name == "tofu":
        version = requested_version
        extension = "zip" if platform_name == "windows" else "tar.gz"
        url = f"https://github.com/opentofu/opentofu/releases/download/v{version}/tofu_{version}_{platform_name}_{arch}.{extension}"
        if platform_name == "windows":
            installed = install_zip_binary(url, "tofu.exe", destination, platform_name)
        else:
            installed = install_targz_binary(url, "tofu", destination, platform_name)
        metadata[name] = version
        write_tool_metadata(metadata, platform_name, arch)
        return installed

    if name == "helm":
        version = requested_version
        if platform_name == "windows":
            url = f"https://get.helm.sh/helm-v{version}-windows-{arch}.zip"
            installed = install_zip_binary(url, f"windows-{arch}/helm.exe", destination, platform_name)
        else:
            url = f"https://get.helm.sh/helm-v{version}-{platform_name}-{arch}.tar.gz"
            installed = install_targz_binary(url, f"{platform_name}-{arch}/helm", destination, platform_name)
        metadata[name] = version
        write_tool_metadata(metadata, platform_name, arch)
        return installed

    if name == "kubectl":
        version = requested_version
        url = (
            f"https://dl.k8s.io/release/v{version}/bin/{platform_name}/{arch}/"
            f"{binary_name_for_platform('kubectl', platform_name)}"
        )
        installed = install_direct_binary(url, destination, platform_name)
        metadata[name] = version
        write_tool_metadata(metadata, platform_name, arch)
        return installed

    if name == "kubeseal":
        version = requested_version
        archive_name = f"kubeseal-{version}-{platform_name}-{arch}.tar.gz"
        url = f"https://github.com/bitnami-labs/sealed-secrets/releases/download/v{version}/{archive_name}"
        installed = install_targz_binary(
            url,
            binary_name_for_platform("kubeseal", platform_name),
            destination,
            platform_name,
        )
        metadata[name] = version
        write_tool_metadata(metadata, platform_name, arch)
        return installed

    if name == "task":
        version = requested_version
        if platform_name == "windows":
            url = f"https://github.com/go-task/task/releases/download/v{version}/task_windows_{arch}.zip"
            installed = install_zip_binary(url, "task.exe", destination, platform_name)
        else:
            url = f"https://github.com/go-task/task/releases/download/v{version}/task_{platform_name}_{arch}.tar.gz"
            installed = install_targz_binary(url, "task", destination, platform_name)
        metadata[name] = version
        write_tool_metadata(metadata, platform_name, arch)
        return installed

    raise HaaCError(f"Unsupported local tool bootstrap: {name}")


def ensure_kubeseal() -> str:
    return ensure_local_cli_tool("kubeseal")


def render_authelia(temp_dir: Path, env: dict[str, str]) -> tuple[Path, Path]:
    run(
        [
            sys.executable,
            str(SCRIPTS_DIR / "hydrate-authelia.py"),
            "--env-file",
            str(ENV_FILE),
            "--output-dir",
            str(temp_dir),
        ],
        env={**os.environ, **env},
    )
    return temp_dir / "authelia_configuration.yml", temp_dir / "authelia_users.yml"


def fetch_or_reuse_public_cert(kubeseal: str, kubeconfig: Path) -> Path:
    ensure_parent(PUB_CERT_PATH)
    completed = run(
        [
            kubeseal,
            "--kubeconfig",
            str(kubeconfig),
            "--fetch-cert",
            "--controller-name=sealed-secrets-controller",
            "--controller-namespace=kube-system",
        ],
        check=False,
        capture_output=True,
    )
    if completed.returncode == 0 and completed.stdout.strip():
        PUB_CERT_PATH.write_text(completed.stdout, encoding="utf-8")
        return PUB_CERT_PATH

    if PUB_CERT_PATH.exists():
        return PUB_CERT_PATH

    detail = completed.stderr.strip() or completed.stdout.strip() or "cluster unreachable"
    raise HaaCError(f"Unable to fetch Sealed Secrets cert and no local cache is available: {detail}")


def create_secret_yaml(
    _kubectl: str,
    name: str,
    namespace: str,
    *,
    literals: dict[str, str] | None = None,
    files: dict[str, Path] | None = None,
    labels: dict[str, str] | None = None,
) -> str:
    return secretlib.render_secret_manifest(name, namespace, literals=literals, files=files, labels=labels)


def seal_yaml(kubeseal: str, cert: Path, yaml_text: str) -> str:
    return run_stdout(
        [
            kubeseal,
            "--format=yaml",
            f"--cert={cert}",
            "--scope",
            "strict",
        ],
        input_text=yaml_text,
    )


def upload_inventory_configmap(kubectl: str, kubeconfig: Path) -> None:
    namespace_yaml = run_stdout(
        [
            kubectl,
            "--kubeconfig",
            str(kubeconfig),
            "create",
            "namespace",
            "mgmt",
            "--dry-run=client",
            "-o",
            "yaml",
        ]
    )
    run([kubectl, "--kubeconfig", str(kubeconfig), "apply", "--validate=false", "-f", "-"], input_text=namespace_yaml)

    configmap_yaml = run_stdout(
        [
            kubectl,
            "--kubeconfig",
            str(kubeconfig),
            "create",
            "configmap",
            "ansible-inventory-cm",
            "-n",
            "mgmt",
            f"--from-file=inventory.yml={ROOT / 'ansible' / 'inventory.yml'}",
            f"--from-file=maintenance-inventory.yml={ROOT / 'ansible' / 'maintenance-inventory.yml'}",
            "--dry-run=client",
            "-o",
            "yaml",
        ]
    )
    run([kubectl, "--kubeconfig", str(kubeconfig), "apply", "--validate=false", "-f", "-"], input_text=configmap_yaml)


def generate_secrets_core(kubeconfig: Path, kubectl: str, *, fetch_cert: bool) -> None:
    env = merged_env()
    require_env(
        [
            "DOMAIN_NAME",
            "GITOPS_REPO_URL",
            "GITOPS_REPO_REVISION",
            "CLOUDFLARE_TUNNEL_TOKEN",
            "PROTONVPN_OPENVPN_USERNAME",
            "PROTONVPN_OPENVPN_PASSWORD",
            "PROTONVPN_SERVER_COUNTRIES",
            "NTFY_TOPIC",
            "ARGOCD_OIDC_SECRET",
            "QUI_PASSWORD",
            "GRAFANA_OIDC_SECRET",
            "SEMAPHORE_DB_PASSWORD",
            "SEMAPHORE_APP_SECRET",
            "SEMAPHORE_OIDC_SECRET",
            "SEMAPHORE_ADMIN_PASSWORD",
        ],
        env,
    )

    kubeseal = ensure_kubeseal()
    cert = fetch_or_reuse_public_cert(kubeseal, kubeconfig) if fetch_cert else PUB_CERT_PATH
    if not cert.exists():
        raise HaaCError("Local Sealed Secrets public cert is missing. Run generate-secrets with cluster access first.")

    SECRETS_DIR.mkdir(parents=True, exist_ok=True)
    temp_dir = Path(tempfile.mkdtemp(prefix="haac-secrets-", dir=ensure_tmp_dir("secrets-runtime")))
    try:
        authelia_configuration, authelia_users = render_authelia(temp_dir, env)
        env["AUTHELIA_CONFIG_CHECKSUM"] = hashlib.sha256(
            (
                authelia_configuration.read_text(encoding="utf-8")
                + "\n---\n"
                + authelia_users.read_text(encoding="utf-8")
            ).encode("utf-8")
        ).hexdigest()

        secrets = [
        (
            "protonvpn-key",
            "media",
            SECRETS_DIR / "protonvpn-sealed-secret.yaml",
            {
                "OPENVPN_USER": f"{env['PROTONVPN_OPENVPN_USERNAME']}+pmp+nr",
                "OPENVPN_PASSWORD": env["PROTONVPN_OPENVPN_PASSWORD"],
                "SERVER_COUNTRIES": env["PROTONVPN_SERVER_COUNTRIES"],
            },
            None,
        ),
        (
            "cloudflare-tunnel-token",
            "cloudflared",
            SECRETS_DIR / "cloudflared-sealed-secret.yaml",
            {"token": env["CLOUDFLARE_TUNNEL_TOKEN"]},
            None,
        ),
        (
            "authelia-config-files",
            "mgmt",
            SECRETS_DIR / "authelia-sealed-secret.yaml",
            None,
            {
                "configuration.yml": authelia_configuration,
                "users.yml": authelia_users,
            },
        ),
        (
            "argocd-notifications-custom-secret",
            "argocd",
            SECRETS_DIR / "argocd-notifications-sealed-secret.yaml",
            {"ntfy-webhook-url": f"http://ntfy.mgmt.svc.cluster.local:80/{env['NTFY_TOPIC']}"},
            None,
        ),
        (
            "downloaders-auth",
            "media",
            SECRETS_DIR / "downloaders-auth-sealed-secret.yaml",
            {
                "QUI_PASSWORD": env["QUI_PASSWORD"],
            },
            None,
        ),
        (
            "homepage-widgets-secret",
            "mgmt",
            HOMEPAGE_WIDGETS_SECRET_OUTPUT,
            {
                "HOMEPAGE_VAR_GRAFANA_USERNAME": "admin",
                "HOMEPAGE_VAR_GRAFANA_PASSWORD": env.get("GRAFANA_ADMIN_PASSWORD", env["QUI_PASSWORD"]),
                "HOMEPAGE_VAR_QBITTORRENT_USERNAME": "admin",
                "HOMEPAGE_VAR_QBITTORRENT_PASSWORD": env["QUI_PASSWORD"],
            },
            None,
        ),
        (
            "grafana-admin-secret",
            "monitoring",
            SECRETS_DIR / "grafana-admin-sealed-secret.yaml",
            {
                "admin-user": "admin",
                "admin-password": env.get("GRAFANA_ADMIN_PASSWORD", env["QUI_PASSWORD"]),
            },
            None,
        ),
        (
            "grafana-oidc-secret",
            "monitoring",
            SECRETS_DIR / "grafana-oidc-sealed-secret.yaml",
            {"GRAFANA_OIDC_SECRET": env["GRAFANA_OIDC_SECRET"]},
            None,
        ),
        (
            "litmus-admin-credentials",
            "chaos",
            LITMUS_ADMIN_SECRET_OUTPUT,
            {
                "ADMIN_USERNAME": env.get("LITMUS_ADMIN_USERNAME", "admin"),
                "ADMIN_PASSWORD": env["LITMUS_ADMIN_PASSWORD"],
            },
            None,
        ),
        (
            "semaphore-db-secret",
            "mgmt",
            SECRETS_DIR / "semaphore-sealed-secret.yaml",
            {
                "POSTGRES_PASSWORD": env["SEMAPHORE_DB_PASSWORD"],
                "ADMIN_PASSWORD": env["SEMAPHORE_ADMIN_PASSWORD"],
                "ADMIN_USERNAME": env.get("SEMAPHORE_ADMIN_USERNAME", "admin"),
                "ADMIN_EMAIL": env.get("SEMAPHORE_ADMIN_EMAIL", "admin@localhost"),
                "ADMIN_NAME": env.get("SEMAPHORE_ADMIN_NAME", "Admin"),
            },
            None,
        ),
        (
            "semaphore-oidc-secret",
            "mgmt",
            SECRETS_DIR / "semaphore-oidc-sealed-secret.yaml",
            {
                "SEMAPHORE_OIDC_PROVIDERS": json.dumps(
                    {
                        "authelia": {
                            "display_name": "Authelia",
                            "provider_url": f"https://auth.{env['DOMAIN_NAME']}",
                            "redirect_url": f"https://ansible.{env['DOMAIN_NAME']}/api/auth/oidc/authelia/redirect",
                            "client_id": "semaphore",
                            "client_secret": env["SEMAPHORE_OIDC_SECRET"],
                            "scopes": ["openid", "profile", "email", "groups"],
                            "username_claim": "preferred_username",
                            "name_claim": "name",
                            "email_claim": f"email | {{{{ .preferred_username }}}}@{env['DOMAIN_NAME']}",
                        }
                    }
                )
            },
            None,
        ),
        (
            "semaphore-general",
            "mgmt",
            SECRETS_DIR / "semaphore-general-sealed-secret.yaml",
            {
                "cookieHash": env.get("SEMAPHORE_COOKIE_HASH", env["SEMAPHORE_APP_SECRET"]),
                "cookieEncryption": env.get("SEMAPHORE_COOKIE_ENCRYPTION", env["SEMAPHORE_APP_SECRET"]),
                "accesskeyEncryption": env["SEMAPHORE_APP_SECRET"],
            },
            None,
        ),
    ]

        ensure_repo_deploy_ssh_keypair()
        maintenance_ssh_key = SEMAPHORE_SSH_PRIVATE_KEY_PATH
        if not maintenance_ssh_key.exists() or not SEMAPHORE_SSH_PUBLIC_KEY_PATH.exists():
            raise HaaCError(
                "Semaphore maintenance SSH keypair is missing. Run `task configure-os` or `task up` first so the "
                "maintenance key is generated and authorized before it is published to the cluster."
            )
        secrets.append(
            (
                "haac-maintenance-ssh-key",
                "mgmt",
                SEMAPHORE_MAINTENANCE_SSH_SECRET_OUTPUT,
                None,
                {
                    "maintenance_ed25519": maintenance_ssh_key,
                    "known_hosts": known_hosts_path(env),
                },
            )
        )

        repo_url = env["GITOPS_REPO_URL"]
        if repo_url_requires_ssh_auth(repo_url):
            repo_deploy_key = REPO_DEPLOY_SSH_PRIVATE_KEY_PATH
            if repo_deploy_key.exists():
                secrets.append(
                    (
                        "haac-repo-deploy-key",
                        "mgmt",
                        SEMAPHORE_REPO_DEPLOY_SSH_SECRET_OUTPUT,
                        None,
                        {"repo_deploy_ed25519": repo_deploy_key},
                    )
                )

        for name, namespace, output_path, literals, files in secrets:
            secret_yaml = create_secret_yaml(kubectl, name, namespace, literals=literals, files=files)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_text(seal_yaml(kubeseal, cert, secret_yaml), encoding="utf-8")

        for legacy_path in (
            SECRETS_DIR / "haac-ssh-sealed-secret.yaml",
            SEMAPHORE_REPO_DEPLOY_SSH_SECRET_OUTPUT if not repo_url_requires_ssh_auth(repo_url) else None,
        ):
            if legacy_path:
                legacy_path.unlink(missing_ok=True)

        argocd_oidc_secret_yaml = create_secret_yaml(
            kubectl,
            "argocd-oidc-secret",
            "argocd",
            literals={"clientSecret": env["ARGOCD_OIDC_SECRET"]},
            labels={"app.kubernetes.io/part-of": "argocd"},
        )
        ARGOCD_OIDC_SECRET_OUTPUT.write_text(seal_yaml(kubeseal, cert, argocd_oidc_secret_yaml), encoding="utf-8")

        render_values_file(env)
        render_gitops_manifests(env)
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


def apply_rendered_file(file_path: Path, kubeconfig: Path, kubectl: str, env: dict[str, str]) -> None:
    content = render_env_placeholders(file_path.read_text(encoding="utf-8"), env)
    run([kubectl, "--kubeconfig", str(kubeconfig), "apply", "--validate=false", "-f", "-"], input_text=content)


def wait_for_jsonpath(
    kubectl: str,
    kubeconfig: Path,
    command: list[str],
    *,
    expected: str,
    timeout_seconds: int,
    interval_seconds: int = 10,
    degraded_check: list[str] | None = None,
    degraded_label: str | None = None,
) -> str:
    deadline = time.time() + timeout_seconds
    last_value = "N/A"
    while time.time() < deadline:
        completed = run(
            [kubectl, "--kubeconfig", str(kubeconfig), *command],
            check=False,
            capture_output=True,
        )
        last_value = completed.stdout.strip()
        if last_value == expected:
            return last_value
        if degraded_check:
            degraded_value = run_stdout([kubectl, "--kubeconfig", str(kubeconfig), *degraded_check], check=False)
            if degraded_value == "Degraded":
                label = degraded_label or " ".join(command)
                raise HaaCError(f"{label} is degraded according to ArgoCD")
        time.sleep(interval_seconds)
    raise HaaCError(f"Timeout waiting for {' '.join(command)} (last value: {last_value})")


def seconds_remaining(deadline: float) -> int:
    return max(1, int(deadline - time.time()))


def wait_for_resource(
    kubectl: str,
    kubeconfig: Path,
    command: list[str],
    *,
    label: str,
    timeout_seconds: int,
    interval_seconds: int = 10,
) -> None:
    deadline = time.time() + timeout_seconds
    while time.time() < deadline:
        completed = run([kubectl, "--kubeconfig", str(kubeconfig), *command], check=False, capture_output=True)
        if completed.returncode == 0:
            return
        time.sleep(interval_seconds)
    raise HaaCError(f"Timeout waiting for {label}")


def gitops_remote_revision_sha(env: dict[str, str], remote_name: str = "origin") -> str | None:
    if not gitstatelib.is_git_repo(ROOT):
        return None
    if not gitstatelib.git_has_remote(ROOT, remote_name):
        return None

    revision = gitops_revision(env)
    remote_ref = f"{remote_name}/{revision}"
    fetch = run(["git", "fetch", remote_name, revision], check=False, capture_output=True)
    require_success(fetch, f"Git fetch failed for {remote_ref}")
    return run_stdout(["git", "rev-parse", remote_ref])


def argocd_application_repo_url(app: dict[str, object]) -> str:
    source = app.get("spec") or {}
    source = source.get("source") or {}
    return str(source.get("repoURL") or "").strip()


def argocd_application_sync_revision(app: dict[str, object]) -> str:
    status = app.get("status") or {}
    sync = status.get("sync") or {}
    return str(sync.get("revision") or "").strip()


def repo_managed_argocd_application_revision_current(
    app: dict[str, object],
    *,
    expected_revision: str | None,
    gitops_repo_url: str | None,
) -> bool:
    if not expected_revision or not gitops_repo_url:
        return True
    if argocd_application_repo_url(app) != gitops_repo_url:
        return True
    return argocd_application_sync_revision(app) == expected_revision


def refresh_argocd_application(kubectl: str, kubeconfig: Path, application: str, *, hard: bool = True) -> None:
    annotation = "argocd.argoproj.io/refresh=hard" if hard else "argocd.argoproj.io/refresh=normal"
    run(
        [
            kubectl,
            "--kubeconfig",
            str(kubeconfig),
            "annotate",
            "application",
            application,
            "-n",
            "argocd",
            annotation,
            "--overwrite",
        ],
        check=False,
    )


def wait_for_argocd_application_ready(
    kubectl: str,
    kubeconfig: Path,
    *,
    application: str,
    stage_label: str,
    deadline: float,
    expected_revision: str | None = None,
    gitops_repo_url: str | None = None,
) -> None:
    print(f"[stage] {stage_label}: {application}")
    resource_command = ["get", "application", application, "-n", "argocd"]
    wait_for_resource(
        kubectl,
        kubeconfig,
        resource_command,
        label=f"ArgoCD application {application}",
        timeout_seconds=seconds_remaining(deadline),
    )
    while time.time() < deadline:
        app = kubectl_json(
            kubectl,
            kubeconfig,
            ["get", "application", application, "-n", "argocd", "-o", "json"],
            context=f"Read ArgoCD application {application}",
        )
        if recover_stale_argocd_operation(kubectl, kubeconfig, application, app):
            time.sleep(5)
            continue
        if application == "haac-stack" and recover_stalled_downloaders_rollout(kubectl, kubeconfig):
            time.sleep(5)
            continue

        status = app.get("status") or {}
        sync_status = ((status.get("sync") or {}).get("status") or "").strip()
        health_status = ((status.get("health") or {}).get("status") or "").strip()
        operation_state = status.get("operationState") or {}
        operation_phase = (operation_state.get("phase") or "").strip()
        revision_current = repo_managed_argocd_application_revision_current(
            app,
            expected_revision=expected_revision,
            gitops_repo_url=gitops_repo_url,
        )

        if sync_status == "Synced" and health_status == "Healthy" and revision_current:
            print(f"[ok] {stage_label}: {application} synced and healthy")
            return
        if sync_status == "Synced" and health_status == "Healthy" and not revision_current:
            current_revision = argocd_application_sync_revision(app) or "unknown"
            refresh_argocd_application(kubectl, kubeconfig, application, hard=True)
            print(
                f"[wait] {stage_label}: {application} healthy on stale revision "
                f"{current_revision[:12]} while waiting for {expected_revision[:12]}"
            )
            time.sleep(10)
            continue

        if operation_phase in {"Error", "Failed"}:
            detail = (operation_state.get("message") or f"ArgoCD application {application} failed").strip()
            raise HaaCError(detail)

        if operation_phase not in {"", "Running"} and health_status == "Degraded":
            detail = (operation_state.get("message") or f"ArgoCD application {application} is degraded according to ArgoCD").strip()
            raise HaaCError(detail)

        time.sleep(10)
    raise HaaCError(f"Timeout waiting for ArgoCD application {application} to become synced and healthy")


def kubectl_json(
    kubectl: str,
    kubeconfig: Path,
    command: list[str],
    *,
    context: str,
) -> dict[str, object]:
    completed = run([kubectl, "--kubeconfig", str(kubeconfig), *command], check=False, capture_output=True)
    require_success(completed, context)
    try:
        return json.loads(completed.stdout or "{}")
    except json.JSONDecodeError as exc:
        raise HaaCError(f"{context}\nInvalid JSON returned by kubectl") from exc


def recover_stale_argocd_operation(
    kubectl: str,
    kubeconfig: Path,
    application: str,
    app: dict[str, object],
) -> bool:
    status = app.get("status") or {}
    operation_state = status.get("operationState") or {}
    operation_phase = (operation_state.get("phase") or "").strip()
    desired_revision = ((status.get("sync") or {}).get("revision") or "").strip()
    active_revision = (((app.get("operation") or {}).get("sync") or {}).get("revision") or "").strip()
    if operation_phase != "Running" or not desired_revision or not active_revision or active_revision == desired_revision:
        return False

    run(
        [
            kubectl,
            "--kubeconfig",
            str(kubeconfig),
            "patch",
            "application",
            application,
            "-n",
            "argocd",
            "--type",
            "json",
            "-p",
            '[{"op":"remove","path":"/operation"}]',
        ],
        check=False,
    )
    run(
        [
            kubectl,
            "--kubeconfig",
            str(kubeconfig),
            "annotate",
            "application",
            application,
            "-n",
            "argocd",
            "argocd.argoproj.io/refresh=hard",
            "--overwrite",
        ],
        check=False,
    )
    print(f"[heal] Reset stale ArgoCD operation for {application}: {active_revision[:12]} -> {desired_revision[:12]}")
    return True


def recover_stalled_downloaders_rollout(kubectl: str, kubeconfig: Path) -> bool:
    if run(
        [kubectl, "--kubeconfig", str(kubeconfig), "get", "serviceaccount", "downloaders-bootstrap", "-n", "media"],
        check=False,
    ).returncode != 0:
        return False

    deployment = kubectl_json(
        kubectl,
        kubeconfig,
        ["get", "deployment", "downloaders", "-n", "media", "-o", "json"],
        context="Read media/downloaders deployment",
    )
    pod_annotations = (
        ((deployment.get("spec") or {}).get("template") or {}).get("metadata") or {}
    ).get("annotations") or {}
    if pod_annotations.get("kubectl.kubernetes.io/restartedAt"):
        return False
    status = deployment.get("status") or {}
    conditions = status.get("conditions") or []
    failed_create = False
    for condition in conditions:
        message = (condition.get("message") or "").lower()
        reason = (condition.get("reason") or "").strip()
        if condition.get("type") == "ReplicaFailure" and "downloaders-bootstrap" in message:
            failed_create = True
            break
        if condition.get("type") == "Progressing" and reason == "ProgressDeadlineExceeded":
            failed_create = True
            break
    if not failed_create:
        return False

    pods = kubectl_json(
        kubectl,
        kubeconfig,
        ["get", "pods", "-n", "media", "-l", "app=downloaders", "-o", "json"],
        context="Read media/downloaders pods",
    )
    if pods.get("items"):
        return False

    run(
        [
            kubectl,
            "--kubeconfig",
            str(kubeconfig),
            "rollout",
            "restart",
            "deployment/downloaders",
            "-n",
            "media",
        ]
    )
    print("[heal] Restarted media/downloaders after dependency recovery")
    return True


def require_success(completed: subprocess.CompletedProcess[str], context: str) -> None:
    if completed.returncode == 0:
        return
    detail = (completed.stderr or completed.stdout or f"exit code {completed.returncode}").strip()
    raise HaaCError(f"{context}\n{redact_text(detail)}")


def require_git_bootstrap_repo(env: dict[str, str], remote_name: str = "origin") -> None:
    if not gitstatelib.is_git_repo(ROOT):
        raise HaaCError("Git repository metadata not found. `task up` requires a writable GitOps clone.")
    if not gitstatelib.git_has_remote(ROOT, remote_name):
        raise HaaCError(
            f"Git remote '{remote_name}' is required so bootstrap changes can be synced and pushed before ArgoCD waits."
        )
    configured_remote = gitstatelib.normalize_git_remote_url(gitstatelib.git_remote_url(ROOT, remote_name))
    expected_remote = gitstatelib.normalize_git_remote_url(gitops_repo_url(env))
    if configured_remote != expected_remote:
        raise HaaCError(
            f"Git remote '{remote_name}' does not match GITOPS_REPO_URL. "
            f"Configured: {configured_remote} Expected: {expected_remote}. "
            "Fix the local remote before running sync, publication, or bootstrap."
        )


def sync_repo() -> None:
    env = merged_env()
    require_git_bootstrap_repo(env)
    revision = gitops_revision(env)

    remote_ref = f"origin/{revision}"
    fetch = run(["git", "fetch", "origin", revision], check=False, capture_output=True)
    require_success(fetch, f"Git fetch failed for {remote_ref}")

    checkpoint_git_changes(
        "Auto-save before sync [skip ci]",
        empty_message="[ok] GitOps repo already checkpointed before sync.",
    )

    ref_state = gitstatelib.git_ref_state(ROOT, "HEAD", remote_ref)
    if ref_state == "equal":
        print(f"[ok] GitOps repo already matches {remote_ref}; no merge needed.")
        return
    if ref_state == "behind":
        fast_forward = run(["git", "merge", "--ff-only", remote_ref], check=False, capture_output=True)
        require_success(fast_forward, f"Fast-forward sync failed for {remote_ref}")
        print(f"[ok] GitOps repo fast-forwarded to {remote_ref}")
        return
    if ref_state == "ahead":
        print(f"[ok] Local branch is already ahead of {remote_ref}; no merge needed.")
        return
    raise HaaCError(
        f"Git sync stopped because local HEAD diverged from {remote_ref}. "
        "Resolve the divergence explicitly with your preferred Git workflow, then rerun `task sync`."
    )


def push_changes(push_all: bool, kubectl: str, kubeconfig: Path) -> None:
    env = merged_env()
    require_git_bootstrap_repo(env)
    revision = gitops_revision(env)

    remote_ref = f"origin/{revision}"
    fetch = run(["git", "fetch", "origin", revision], check=False, capture_output=True)
    require_success(fetch, f"Git fetch failed for {remote_ref}")
    ref_state = gitstatelib.git_ref_state(ROOT, "HEAD", remote_ref)
    if ref_state in {"behind", "diverged"}:
        raise HaaCError(
            "GitOps publication is publish-only and will not merge remote state. "
            f"Local HEAD is {ref_state} relative to {remote_ref}. "
            "Run `task sync` first, then rerun the publish or bootstrap command."
        )
    if push_all:
        checkpoint_git_changes(
            "Auto-commit manual work [skip ci]",
            empty_message="[ok] No local repo changes needed a checkpoint before GitOps publication.",
        )

    generate_secrets_core(kubeconfig, kubectl, fetch_cert=False)

    if push_all:
        stage_git_paths()
    else:
        stage_git_paths([str(SECRETS_DIR), str(VALUES_OUTPUT), *[str(path) for path in GITOPS_RENDERED_OUTPUTS]])

    if not git_has_staged_changes():
        print("[ok] GitOps output already converged; nothing new to publish.")
    else:
        published = run(["git", "commit", "-m", "Updated infrastructure [skip ci]", "--no-verify"], check=False, capture_output=True)
        require_success(published, "GitOps publication commit failed")
        print(f"[ok] GitOps publication commit: {run_stdout(['git', 'rev-parse', 'HEAD'])}")

    pushed = run(["git", "push", "origin", revision], check=False, capture_output=True)
    require_success(pushed, f"Git push failed for {revision}")
    commit = run_stdout(["git", "rev-parse", "HEAD"])
    print(f"Pushed GitOps source of truth: {commit} -> origin/{revision}")


def install_hooks() -> None:
    if not HOOKS_DIR.exists():
        print("Skipping hook installation: .git/hooks not found.")
        return

    hook = HOOKS_DIR / "pre-commit"
    hook.write_text(
        "#!/usr/bin/env python3\n"
        "import pathlib, subprocess, sys\n"
        "root = pathlib.Path(__file__).resolve().parents[2]\n"
        "cmd = [sys.executable or 'python', str(root / 'scripts' / 'haac.py'), 'pre-commit-hook']\n"
        "raise SystemExit(subprocess.call(cmd, cwd=root))\n",
        encoding="utf-8",
    )
    if not is_windows():
        hook.chmod(0o755)

    hook_cmd = HOOKS_DIR / "pre-commit.cmd"
    hook_cmd.write_text(
        "@echo off\r\n"
        "python \"%~dp0\\..\\..\\scripts\\haac.py\" pre-commit-hook\r\n"
        "exit /b %ERRORLEVEL%\r\n",
        encoding="utf-8",
    )


def pre_commit_hook() -> None:
    kubeconfig = local_kubeconfig_path()
    kubectl = resolved_binary("kubectl")
    if kubeconfig.exists():
        health = run([kubectl, "--kubeconfig", str(kubeconfig), "get", "ns", "kube-system"], check=False)
        if health.returncode == 0:
            generate_secrets_core(kubeconfig, kubectl, fetch_cert=True)
            if gitstatelib.is_git_repo(ROOT):
                run(
                    ["git", "add", str(SECRETS_DIR), str(VALUES_OUTPUT), *[str(path) for path in GITOPS_RENDERED_OUTPUTS]],
                    check=False,
                )
            return

    print("K3s is not reachable from the pre-commit hook. Skipping secret regeneration.")


def cleanup_legacy_default_argocd_install(kubectl: str, kubeconfig: Path) -> None:
    existing = run(
        [
            kubectl,
            "--kubeconfig",
            str(kubeconfig),
            "get",
            "deployment,statefulset,service,configmap,secret,serviceaccount,role,rolebinding,networkpolicy",
            "-n",
            "default",
            "-o",
            "name",
        ],
        check=False,
        capture_output=True,
    )
    if existing.returncode != 0:
        return

    legacy_resources = []
    for resource_name in (existing.stdout or "").splitlines():
        resource_name = resource_name.strip()
        if not resource_name:
            continue
        _, _, name = resource_name.partition("/")
        if name.startswith("argocd-"):
            legacy_resources.append(resource_name)

    if not legacy_resources:
        return

    deleted = run(
        [
            kubectl,
            "--kubeconfig",
            str(kubeconfig),
            "delete",
            "-n",
            "default",
            "--ignore-not-found=true",
            "--wait=false",
            *legacy_resources,
        ],
        check=False,
        capture_output=True,
    )
    output = (deleted.stdout or deleted.stderr or "").strip()
    if deleted.returncode == 0 and output:
        print("[ok] Removed legacy ArgoCD bootstrap resources from namespace default")


def deploy_argocd(master_ip: str, proxmox_host: str, kubeconfig: Path, kubectl: str) -> None:
    env = merged_env()
    with cluster_session(proxmox_host, master_ip, kubeconfig, kubectl) as session_kubeconfig:
        run(
            [
                kubectl,
                "--kubeconfig",
                str(session_kubeconfig),
                "apply",
                "--server-side",
                "--force-conflicts",
                "--validate=false",
                "-k",
                str(K8S_DIR / "platform" / "argocd" / "install-overlay"),
            ]
        )
        run(
            [
                kubectl,
                "--kubeconfig",
                str(session_kubeconfig),
                "rollout",
                "restart",
                "deployment/argocd-server",
                "-n",
                "argocd",
            ]
        )
        run(
            [
                kubectl,
                "--kubeconfig",
                str(session_kubeconfig),
                "rollout",
                "status",
                "deployment/argocd-server",
                "-n",
                "argocd",
                "--timeout=300s",
            ]
        )
        cleanup_legacy_default_argocd_install(kubectl, session_kubeconfig)
        cleanup_falco_legacy_ui_storage(kubectl, session_kubeconfig, env)
        root_app = render_env_placeholders((K8S_DIR / "argocd-apps.yaml").read_text(encoding="utf-8"), env)
        run([kubectl, "--kubeconfig", str(session_kubeconfig), "apply", "--validate=false", "-f", "-"], input_text=root_app)
        refresh_argocd_application(kubectl, session_kubeconfig, "haac-root", hard=True)
        cleanup_disabled_platform_apps(kubectl, session_kubeconfig, env)


def seed_argocd_bootstrap_patch(kubectl: str, kubeconfig: Path, timeout_seconds: int = 120) -> None:
    if not ARGOCD_REPOSERVER_PATCH.exists():
        return

    deadline = time.time() + timeout_seconds
    while time.time() < deadline:
        exists = run(
            [kubectl, "--kubeconfig", str(kubeconfig), "get", "deployment", "argocd-repo-server", "-n", "argocd"],
            check=False,
        )
        if exists.returncode == 0:
            run(
                [
                    kubectl,
                    "--kubeconfig",
                    str(kubeconfig),
                    "patch",
                    "deployment",
                    "argocd-repo-server",
                    "-n",
                    "argocd",
                    "--type=json",
                    f"--patch-file={ARGOCD_REPOSERVER_PATCH}",
                ]
            )
            rollout = run(
                [
                    kubectl,
                    "--kubeconfig",
                    str(kubeconfig),
                    "rollout",
                    "status",
                    "deployment/argocd-repo-server",
                    "-n",
                    "argocd",
                    "--timeout=180s",
                ],
                check=False,
                capture_output=True,
            )
            require_success(rollout, "ArgoCD repo-server bootstrap patch did not become ready")
            print("[ok] Seeded ArgoCD repo-server bootstrap patch")
            return
        time.sleep(5)

    print("[warn] ArgoCD repo-server deployment not present yet; continuing without bootstrap patch seed")


def deploy_local(master_ip: str, proxmox_host: str, kubeconfig: Path, kubectl: str, helm: str) -> None:
    env = merged_env()
    with cluster_session(proxmox_host, master_ip, kubeconfig, kubectl) as session_kubeconfig:
        apply_rendered_file(K8S_DIR / "bootstrap" / "root" / "namespaces.yaml", session_kubeconfig, kubectl, env)
        run(
            [
                kubectl,
                "--kubeconfig",
                str(session_kubeconfig),
                "apply",
                "--server-side",
                "-f",
                f"https://github.com/rancher/system-upgrade-controller/releases/download/{SYSTEM_UPGRADE_CONTROLLER_VERSION}/crd.yaml",
            ],
            check=False,
        )
        run(
            [
                kubectl,
                "--kubeconfig",
                str(session_kubeconfig),
                "wait",
                "--for=condition=established",
                "crd/plans.upgrade.cattle.io",
                "--timeout=60s",
            ],
            check=False,
        )

        exists = run(
            [
                kubectl,
                "--kubeconfig",
                str(session_kubeconfig),
                "get",
                "application",
                "haac-stack",
                "-n",
                "argocd",
            ],
            check=False,
        )
        if exists.returncode == 0:
            print("ArgoCD already manages haac-stack. Skipping local helm upgrade.")
            return

        run(
            [
                helm,
                "--kubeconfig",
                str(session_kubeconfig),
                "upgrade",
                "--install",
                "haac-stack",
                str(K8S_DIR / "charts" / "haac-stack"),
                "-n",
                "mgmt",
                "--create-namespace",
            ]
        )


def wait_for_stack(master_ip: str, proxmox_host: str, kubeconfig: Path, kubectl: str, timeout_seconds: int = 3600) -> None:
    env = merged_env()
    gitops_repo = gitops_repo_url(env)
    expected_revision = gitops_remote_revision_sha(env)
    with cluster_session(proxmox_host, master_ip, kubeconfig, kubectl) as session_kubeconfig:
        last_verified_phase = "GitOps publication"

        def wait_for_readiness_gate(application: str, stage_label: str) -> None:
            nonlocal last_verified_phase
            try:
                wait_for_argocd_application_ready(
                    kubectl,
                    session_kubeconfig,
                    application=application,
                    stage_label=stage_label,
                    deadline=deadline,
                    expected_revision=expected_revision,
                    gitops_repo_url=gitops_repo,
                )
            except HaaCError as exc:
                raise HaaCError(
                    bootstrap_recovery_summary(
                        failing_phase="GitOps readiness",
                        last_verified_phase=last_verified_phase,
                        rerun_guidance=UP_PHASE_RERUN_GUIDANCE["GitOps readiness"],
                        detail=str(exc),
                    )
                ) from exc
            last_verified_phase = stage_label

        print("[stage] ArgoCD API reachability")
        if run([kubectl, "--kubeconfig", str(session_kubeconfig), "get", "applications", "-n", "argocd"], check=False).returncode != 0:
            raise HaaCError(
                bootstrap_recovery_summary(
                    failing_phase="GitOps readiness",
                    last_verified_phase=last_verified_phase,
                    rerun_guidance=UP_PHASE_RERUN_GUIDANCE["GitOps readiness"],
                    detail="ArgoCD API server is not reachable",
                )
            )
        print("[ok] ArgoCD API reachability")
        last_verified_phase = "ArgoCD API reachability"

        deadline = time.time() + timeout_seconds
        wait_for_readiness_gate("haac-root", "Root application gate")
        wait_for_readiness_gate("haac-platform", "Platform root gate")
        wait_for_readiness_gate("argocd", "ArgoCD self-management gate")
        wait_for_readiness_gate("haac-workloads", "Workloads root gate")
        wait_for_readiness_gate("haac-stack", "Workload application gate")

        print("[stage] Workload secret gate: media/protonvpn-key")
        while time.time() < deadline:
            if run([kubectl, "--kubeconfig", str(session_kubeconfig), "get", "secret", "protonvpn-key", "-n", "media"], check=False).returncode == 0:
                print("[ok] Workload secret gate: media/protonvpn-key")
                last_verified_phase = "Workload secret gate"
                break
            time.sleep(10)
        else:
            raise HaaCError(
                bootstrap_recovery_summary(
                    failing_phase="GitOps readiness",
                    last_verified_phase=last_verified_phase,
                    rerun_guidance=UP_PHASE_RERUN_GUIDANCE["GitOps readiness"],
                    detail="Timed out waiting for secret media/protonvpn-key",
                )
            )

        print("[stage] Downloader readiness gate")
        while time.time() < deadline:
            ready = run_stdout(
                [
                    kubectl,
                    "--kubeconfig",
                    str(session_kubeconfig),
                    "get",
                    "pods",
                    "-n",
                    "media",
                    "-l",
                    "app=downloaders",
                    "-o",
                    'jsonpath={.items[0].status.conditions[?(@.type=="Ready")].status}',
                ],
                check=False,
            )
            if ready == "True":
                bootstrap_job = run(
                    [
                        kubectl,
                        "--kubeconfig",
                        str(session_kubeconfig),
                        "get",
                        "job",
                        "downloaders-bootstrap",
                        "-n",
                        "media",
                    ],
                    check=False,
                    capture_output=True,
                )
                if bootstrap_job.returncode == 0:
                    waited = run(
                        [
                            kubectl,
                            "--kubeconfig",
                            str(session_kubeconfig),
                            "wait",
                            "--for=condition=complete",
                            "job/downloaders-bootstrap",
                            "-n",
                            "media",
                            "--timeout=300s",
                        ],
                        check=False,
                        capture_output=True,
                    )
                    try:
                        require_success(waited, "downloaders-bootstrap job did not complete successfully")
                    except HaaCError as exc:
                        raise HaaCError(
                            bootstrap_recovery_summary(
                                failing_phase="GitOps readiness",
                                last_verified_phase=last_verified_phase,
                                rerun_guidance=UP_PHASE_RERUN_GUIDANCE["GitOps readiness"],
                                detail=str(exc),
                            )
                        ) from exc
                print("[ok] Downloader readiness gate")
                last_verified_phase = "Downloader readiness gate"
                return
            time.sleep(10)
        raise HaaCError(
            bootstrap_recovery_summary(
                failing_phase="GitOps readiness",
                last_verified_phase=last_verified_phase,
                rerun_guidance=UP_PHASE_RERUN_GUIDANCE["GitOps readiness"],
                detail="Timed out waiting for downloaders pod readiness",
            )
        )


def verify_cluster(master_ip: str, proxmox_host: str, kubeconfig: Path, kubectl: str) -> None:
    with cluster_session(proxmox_host, master_ip, kubeconfig, kubectl) as session_kubeconfig:
        sections = [
            (["get", "nodes", "-o", "wide"], "--- Node Status ---"),
            (["get", "pods", "-A"], "--- Pod Health ---"),
            (["get", "nodes", "-o", 'custom-columns=NAME:.metadata.name,GPU_ALLOCATABLE:.status.allocatable.nvidia\\.com/gpu'], "--- GPU Allocation ---"),
            (["get", "pods", "-n", "kube-system", "-l", "name=nvidia-device-plugin-ds"], "--- NVIDIA Device Plugin Pods ---"),
            (["get", "pvc", "-A"], "--- PVCs ---"),
            (["get", "pv"], "--- PVs ---"),
            (["get", "ingress", "-A"], "--- Ingress ---"),
        ]
        for command, title in sections:
            print(title)
            completed = run(
                [kubectl, "--kubeconfig", str(session_kubeconfig), "--request-timeout=60s", *command],
                check=False,
                capture_output=True,
            )
            print((completed.stdout or completed.stderr).strip())
            print()

        certificate_resource = run(
            [kubectl, "--kubeconfig", str(session_kubeconfig), "--request-timeout=60s", "api-resources", "-o", "name"],
            check=False,
            capture_output=True,
        )
        certificate_resources = certificate_resource.stdout or ""
        if re.search(r"(?m)^certificates(?:\..+)?$", certificate_resources):
            print("--- Certificates ---")
            completed = run(
                [kubectl, "--kubeconfig", str(session_kubeconfig), "--request-timeout=60s", "get", "certificates", "-A"],
                check=False,
                capture_output=True,
            )
            print((completed.stdout or completed.stderr).strip())
            print()


def decode_secret_data(secret: dict[str, object]) -> dict[str, str]:
    data = secret.get("data")
    if not isinstance(data, dict):
        return {}
    decoded: dict[str, str] = {}
    for key, value in data.items():
        if not isinstance(value, str):
            continue
        decoded[key] = base64.b64decode(value).decode("utf-8")
    return decoded


def wait_for_local_port(port: int, timeout_seconds: int = 20) -> None:
    deadline = time.time() + timeout_seconds
    while time.time() < deadline:
        try:
            with socket.create_connection(("127.0.0.1", port), timeout=1):
                return
        except OSError:
            time.sleep(0.5)
    raise HaaCError(f"Timed out waiting for local port {port} to accept connections")


@contextmanager
def kubectl_port_forward(
    kubectl: str,
    kubeconfig: Path,
    namespace: str,
    resource: str,
    remote_port: int,
) -> int:
    runtime_dir = TMP_DIR / "port-forward"
    runtime_dir.mkdir(parents=True, exist_ok=True)
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as listener:
        listener.bind(("127.0.0.1", 0))
        local_port = listener.getsockname()[1]
    log_path = runtime_dir / f"{namespace}-{resource.replace('/', '-')}-{local_port}.log"
    with log_path.open("w", encoding="utf-8") as log_handle:
        process = subprocess.Popen(
            [
                kubectl,
                "--kubeconfig",
                str(kubeconfig),
                "port-forward",
                "-n",
                namespace,
                resource,
                f"{local_port}:{remote_port}",
            ],
            stdout=log_handle,
            stderr=subprocess.STDOUT,
            text=True,
        )
        try:
            wait_for_local_port(local_port)
            yield local_port
        finally:
            process.terminate()
            try:
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=10)


def litmus_login_probe(port: int, username: str, password: str) -> tuple[int, str]:
    payload = json.dumps({"username": username, "password": password}).encode("utf-8")
    request = urllib.request.Request(
        f"http://127.0.0.1:{port}/login",
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            return response.status, response.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read().decode("utf-8")


LITMUS_DEFAULT_ENVIRONMENT_ID = "haac-default"
LITMUS_DEFAULT_ENVIRONMENT_NAME = "haac-default"
LITMUS_LEGACY_ENVIRONMENT_ID = "test"
LITMUS_DEFAULT_ENVIRONMENT_DESCRIPTION = "HaaC default chaos environment"
LITMUS_DEFAULT_INFRA_NAME = "haac-default"
LITMUS_DEFAULT_INFRA_DESCRIPTION = "HaaC default chaos infrastructure"
LITMUS_DEFAULT_INFRA_NAMESPACE = "litmus"
LITMUS_DEFAULT_INFRA_SERVICE_ACCOUNT = "litmus"
LITMUS_ENVIRONMENT_TYPE = "NON_PROD"
LITMUS_INFRA_TYPE = "Kubernetes"
LITMUS_PLATFORM_NAME = "Kubernetes"
LITMUS_INFRA_SCOPE = "cluster"
LITMUS_FRONTEND_INTERNAL_URL = "http://litmus-frontend-service.chaos.svc.cluster.local:9091"
LITMUS_BACKEND_INTERNAL_URL = "http://litmus-server-service.chaos.svc.cluster.local:9002"
LITMUS_AGENT_DEPLOYMENTS = (
    "chaos-operator-ce",
    "chaos-exporter",
    "subscriber",
    "event-tracker",
    "workflow-controller",
)


def litmus_http_json(
    url: str,
    *,
    method: str = "GET",
    payload: dict[str, object] | None = None,
    token: str | None = None,
    referer: str | None = None,
    timeout: int = 60,
) -> dict[str, object]:
    data = None
    headers = {"Accept": "application/json"}
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"
    if token:
        headers["Authorization"] = f"Bearer {token}"
    if referer:
        headers["Referer"] = referer
    request = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            body = response.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8")
        raise HaaCError(f"Litmus API request failed: {method} {url}\n{detail}") from exc
    try:
        return json.loads(body)
    except json.JSONDecodeError as exc:
        raise HaaCError(f"Litmus API returned non-JSON content: {method} {url}") from exc


def litmus_auth_login(port: int, username: str, password: str) -> dict[str, object]:
    response = litmus_http_json(
        f"http://127.0.0.1:{port}/login",
        method="POST",
        payload={"username": username, "password": password},
    )
    access_token = str(response.get("accessToken") or "")
    project_id = str(response.get("projectID") or "")
    if not access_token or not project_id:
        raise HaaCError("Litmus auth login did not return an access token and project ID")
    return response


def litmus_graphql(
    port: int,
    token: str,
    query: str,
    variables: dict[str, object],
    *,
    referer: str = LITMUS_FRONTEND_INTERNAL_URL,
) -> dict[str, object]:
    response = litmus_http_json(
        f"http://127.0.0.1:{port}/query",
        method="POST",
        payload={"query": query, "variables": variables},
        token=token,
        referer=referer,
    )
    errors = response.get("errors")
    if isinstance(errors, list) and errors:
        detail = json.dumps(errors, ensure_ascii=False)
        raise HaaCError(f"Litmus GraphQL request failed:\n{detail}")
    data = response.get("data")
    if not isinstance(data, dict):
        raise HaaCError("Litmus GraphQL request returned no data payload")
    return data


def litmus_list_environments(server_port: int, token: str, project_id: str) -> list[dict[str, object]]:
    data = litmus_graphql(
        server_port,
        token,
        "query ListEnvironments($projectID: ID!) { listEnvironments(projectID: $projectID) { totalNoOfEnvironments environments { environmentID name description type infraIDs } } }",
        {"projectID": project_id},
    )
    payload = data.get("listEnvironments") or {}
    environments = payload.get("environments") or []
    return [item for item in environments if isinstance(item, dict)]


def litmus_create_environment(server_port: int, token: str, project_id: str, environment_id: str, name: str) -> dict[str, object]:
    data = litmus_graphql(
        server_port,
        token,
        "mutation CreateEnvironment($projectID: ID!, $request: CreateEnvironmentRequest!) { createEnvironment(projectID: $projectID, request: $request) { environmentID name description type infraIDs } }",
        {
            "projectID": project_id,
            "request": {
                "environmentID": environment_id,
                "name": name,
                "type": LITMUS_ENVIRONMENT_TYPE,
                "description": LITMUS_DEFAULT_ENVIRONMENT_DESCRIPTION,
                "tags": ["haac", "default"],
            },
        },
    )
    created = data.get("createEnvironment")
    if not isinstance(created, dict):
        raise HaaCError("Litmus did not return the created environment")
    return created


def litmus_list_infras(server_port: int, token: str, project_id: str) -> list[dict[str, object]]:
    data = litmus_graphql(
        server_port,
        token,
        "query ListInfras($projectID: ID!) { listInfras(projectID: $projectID) { totalNoOfInfras infras { infraID name description environmentID infraNamespace serviceAccount infraScope isActive isInfraConfirmed token } } }",
        {"projectID": project_id},
    )
    payload = data.get("listInfras") or {}
    infras = payload.get("infras") or []
    return [item for item in infras if isinstance(item, dict)]


def litmus_delete_infra(server_port: int, token: str, project_id: str, infra_id: str) -> None:
    litmus_graphql(
        server_port,
        token,
        "mutation DeleteInfra($projectID: ID!, $infraID: String!) { deleteInfra(projectID: $projectID, infraID: $infraID) }",
        {"projectID": project_id, "infraID": infra_id},
    )


def litmus_register_infra(server_port: int, token: str, project_id: str, environment_id: str, infra_name: str) -> dict[str, object]:
    data = litmus_graphql(
        server_port,
        token,
        "mutation RegisterInfra($projectID: ID!, $request: RegisterInfraRequest!) { registerInfra(projectID: $projectID, request: $request) { infraID token name manifest } }",
        {
            "projectID": project_id,
            "request": {
                "name": infra_name,
                "description": LITMUS_DEFAULT_INFRA_DESCRIPTION,
                "environmentID": environment_id,
                "infrastructureType": LITMUS_INFRA_TYPE,
                "platformName": LITMUS_PLATFORM_NAME,
                "infraScope": LITMUS_INFRA_SCOPE,
                "infraNamespace": LITMUS_DEFAULT_INFRA_NAMESPACE,
                "serviceAccount": LITMUS_DEFAULT_INFRA_SERVICE_ACCOUNT,
                "infraNsExists": False,
                "infraSaExists": False,
                "skipSsl": False,
                "tags": ["haac", "default"],
            },
        },
    )
    registered = data.get("registerInfra")
    if not isinstance(registered, dict):
        raise HaaCError("Litmus did not return the registered infrastructure payload")
    manifest = str(registered.get("manifest") or "")
    if not manifest:
        raise HaaCError("Litmus did not return the infrastructure manifest")
    return registered


def select_litmus_reconcile_targets(environments: list[dict[str, object]]) -> list[tuple[str, str, bool]]:
    by_id = {str(item.get("environmentID") or ""): item for item in environments}
    if LITMUS_DEFAULT_ENVIRONMENT_ID in by_id:
        current = by_id[LITMUS_DEFAULT_ENVIRONMENT_ID]
        return [
            (
                LITMUS_DEFAULT_ENVIRONMENT_ID,
                str(current.get("name") or LITMUS_DEFAULT_ENVIRONMENT_NAME),
                False,
            )
        ]
    return [(LITMUS_DEFAULT_ENVIRONMENT_ID, LITMUS_DEFAULT_ENVIRONMENT_NAME, True)]


def wait_for_litmus_agent_rollout(kubectl: str, kubeconfig: Path) -> None:
    for deployment in LITMUS_AGENT_DEPLOYMENTS:
        run(
            [
                kubectl,
                "--kubeconfig",
                str(kubeconfig),
                "rollout",
                "status",
                f"deployment/{deployment}",
                "-n",
                LITMUS_DEFAULT_INFRA_NAMESPACE,
                "--timeout=240s",
            ]
        )


def wait_for_litmus_infra_active(server_port: int, token: str, project_id: str, infra_name: str, environment_id: str, timeout_seconds: int = 300) -> dict[str, object]:
    deadline = time.time() + timeout_seconds
    last_state = ""
    while time.time() < deadline:
        infras = litmus_list_infras(server_port, token, project_id)
        for infra in infras:
            if str(infra.get("environmentID") or "") != environment_id:
                continue
            if str(infra.get("name") or "") != infra_name:
                continue
            if bool(infra.get("isActive")) and bool(infra.get("isInfraConfirmed")):
                return infra
            last_state = json.dumps(
                {
                    "infraID": infra.get("infraID"),
                    "name": infra.get("name"),
                    "isActive": infra.get("isActive"),
                    "isInfraConfirmed": infra.get("isInfraConfirmed"),
                },
                ensure_ascii=False,
            )
        time.sleep(5)
    raise HaaCError(
        "Litmus infrastructure did not become active and confirmed within the timeout"
        + (f": {last_state}" if last_state else "")
    )


def reconcile_litmus_environment_target(
    server_port: int,
    token: str,
    project_id: str,
    environment_id: str,
    environment_name: str,
    *,
    should_create_environment: bool,
    kubectl: str,
    kubeconfig: Path,
) -> None:
    if should_create_environment:
        litmus_create_environment(server_port, token, project_id, environment_id, environment_name)
        print(f"[ok] Litmus default environment created: {environment_name} ({environment_id})")
    else:
        print(f"[ok] Litmus environment ready: {environment_name} ({environment_id})")

    infras = litmus_list_infras(server_port, token, project_id)
    active_infras = [
        infra
        for infra in infras
        if str(infra.get("environmentID") or "") == environment_id and bool(infra.get("isActive")) and bool(infra.get("isInfraConfirmed"))
    ]
    if active_infras:
        active = active_infras[0]
        print(
            f"[ok] Litmus chaos infrastructure already active: "
            f"{active.get('name')} ({active.get('infraID')}) in {environment_id}"
        )
        return

    infra_name = LITMUS_DEFAULT_INFRA_NAME
    stale_default_infras = [
        infra
        for infra in infras
        if str(infra.get("environmentID") or "") == environment_id
        and str(infra.get("name") or "") == infra_name
    ]
    for infra in stale_default_infras:
        infra_id = str(infra.get("infraID") or "")
        if infra_id:
            litmus_delete_infra(server_port, token, project_id, infra_id)
            print(f"[ok] Litmus stale infrastructure record removed: {infra_id}")

    registered = litmus_register_infra(server_port, token, project_id, environment_id, infra_name)
    manifest = str(registered["manifest"])
    infra_id = str(registered["infraID"])
    run(
        [kubectl, "--kubeconfig", str(kubeconfig), "apply", "-f", "-"],
        input_text=manifest,
    )
    wait_for_litmus_agent_rollout(kubectl, kubeconfig)
    active = wait_for_litmus_infra_active(server_port, token, project_id, infra_name, environment_id)
    print(
        f"[ok] Litmus chaos infrastructure active: "
        f"{active.get('name')} ({active.get('infraID') or infra_id}) in {environment_id}"
    )


def litmus_hide_legacy_environment(
    kubectl: str,
    kubeconfig: Path,
    mongo_uri: str,
    *,
    username: str,
) -> bool:
    update_script = (
        'const actor={user_id:"",username:'
        + json.dumps(username)
        + ',email:""};'
        "const now=Date.now();"
        'const env=db.getSiblingDB("litmus").environment.updateMany('
        '{environment_id:"test",is_removed:false},'
        '{\\$set:{is_removed:true,updated_at:now,updated_by:actor}}'
        ");"
        'const infra=db.getSiblingDB("litmus").chaosInfrastructures.updateMany('
        '{environment_id:"test",is_removed:false},'
        '{\\$set:{is_removed:true,is_registered:false,is_active:false,is_infra_confirmed:false,updated_at:now,updated_by:actor}}'
        ");"
        "print(JSON.stringify({envModified:env.modifiedCount,infraModified:infra.modifiedCount}));"
    )
    completed = run(
        [
            kubectl,
            "--kubeconfig",
            str(kubeconfig),
            "exec",
            "-n",
            "chaos",
            "statefulset/litmus-mongodb",
            "--",
            "mongosh",
            "--quiet",
            mongo_uri,
            "--eval",
            update_script,
        ],
        capture_output=True,
    )
    payload = json.loads((completed.stdout or "{}").strip() or "{}")
    changed = int(payload.get("envModified") or 0) > 0 or int(payload.get("infraModified") or 0) > 0
    if changed:
        run([kubectl, "--kubeconfig", str(kubeconfig), "rollout", "restart", "deployment/litmus-server", "-n", "chaos"])
        run(
            [
                kubectl,
                "--kubeconfig",
                str(kubeconfig),
                "rollout",
                "status",
                "deployment/litmus-server",
                "-n",
                "chaos",
                "--timeout=180s",
            ]
        )
    return changed


def reconcile_litmus_chaos(master_ip: str, proxmox_host: str, kubeconfig: Path, kubectl: str) -> None:
    env = merged_env()
    username = env.get("LITMUS_ADMIN_USERNAME", "admin")
    password = env.get("LITMUS_ADMIN_PASSWORD") or env.get("AUTHELIA_ADMIN_PASSWORD")
    if not password:
        print("[skip] Litmus chaos reconciliation skipped: no LITMUS_ADMIN_PASSWORD or AUTHELIA_ADMIN_PASSWORD configured")
        return

    with cluster_session(proxmox_host, master_ip, kubeconfig, kubectl) as session_kubeconfig:
        if run([kubectl, "--kubeconfig", str(session_kubeconfig), "get", "deploy", "litmus-auth-server", "-n", "chaos"], check=False).returncode != 0:
            print("[skip] Litmus chaos reconciliation skipped: litmus-auth-server deployment is not present")
            return
        if run([kubectl, "--kubeconfig", str(session_kubeconfig), "get", "deploy", "litmus-server", "-n", "chaos"], check=False).returncode != 0:
            print("[skip] Litmus chaos reconciliation skipped: litmus-server deployment is not present")
            return

        auth_service = kubectl_json(
            kubectl,
            session_kubeconfig,
            ["get", "svc", "litmus-auth-server-service", "-n", "chaos", "-o", "json"],
            context="Unable to read Litmus auth service",
        )
        auth_port = int(((auth_service.get("spec") or {}).get("ports") or [{}])[0].get("port") or 0)
        if auth_port <= 0:
            raise HaaCError("Unable to determine the Litmus auth service port")

        server_service = kubectl_json(
            kubectl,
            session_kubeconfig,
            ["get", "svc", "litmus-server-service", "-n", "chaos", "-o", "json"],
            context="Unable to read Litmus server service",
        )
        server_port = int(((server_service.get("spec") or {}).get("ports") or [{}])[0].get("port") or 0)
        if server_port <= 0:
            raise HaaCError("Unable to determine the Litmus server service port")

        mongodb_secret = kubectl_json(
            kubectl,
            session_kubeconfig,
            ["get", "secret", "litmus-mongodb", "-n", "chaos", "-o", "json"],
            context="Unable to read Litmus MongoDB secret",
        )
        mongodb_data = decode_secret_data(mongodb_secret)
        mongodb_root_password = mongodb_data.get("mongodb-root-password")
        if not mongodb_root_password:
            raise HaaCError("Litmus MongoDB root password is missing from secret litmus-mongodb")
        mongo_uri = (
            "mongodb://root:"
            f"{urllib.parse.quote(mongodb_root_password, safe='')}"
            "@127.0.0.1:27017/admin?authSource=admin"
        )

        with kubectl_port_forward(kubectl, session_kubeconfig, "chaos", "svc/litmus-auth-server-service", auth_port) as auth_pf, kubectl_port_forward(
            kubectl, session_kubeconfig, "chaos", "svc/litmus-server-service", server_port
        ) as server_pf:
            login = litmus_auth_login(auth_pf, username, password)
            project_id = str(login["projectID"])
            token = str(login["accessToken"])

            environments = litmus_list_environments(server_pf, token, project_id)
            targets = select_litmus_reconcile_targets(environments)
            for environment_id, environment_name, should_create_environment in targets:
                reconcile_litmus_environment_target(
                    server_pf,
                    token,
                    project_id,
                    environment_id,
                    environment_name,
                    should_create_environment=should_create_environment,
                    kubectl=kubectl,
                    kubeconfig=session_kubeconfig,
                )
            if any(str(item.get("environmentID") or "") == LITMUS_LEGACY_ENVIRONMENT_ID for item in environments):
                if litmus_hide_legacy_environment(kubectl, session_kubeconfig, mongo_uri, username=username):
                    print("[ok] Litmus legacy test environment hidden after canonical environment bootstrap")
                else:
                    print("[ok] Litmus legacy test environment already hidden")


def litmus_clear_initial_login(
    kubectl: str,
    kubeconfig: Path,
    mongo_uri: str,
    *,
    username: str,
) -> None:
    update_script = (
        'db.getSiblingDB("auth").users.updateOne('
        f'{{username:{json.dumps(username)}}}, '
        '{\\$set:{is_initial_login:false}}'
        ')'
    )
    run(
        [
            kubectl,
            "--kubeconfig",
            str(kubeconfig),
            "exec",
            "-n",
            "chaos",
            "statefulset/litmus-mongodb",
            "--",
            "mongosh",
            "--quiet",
            mongo_uri,
            "--eval",
            update_script,
        ]
    )


def reconcile_litmus_admin(master_ip: str, proxmox_host: str, kubeconfig: Path, kubectl: str) -> None:
    env = merged_env()
    username = env.get("LITMUS_ADMIN_USERNAME", "admin")
    password = env.get("LITMUS_ADMIN_PASSWORD") or env.get("AUTHELIA_ADMIN_PASSWORD")
    if not password:
        print("[skip] Litmus admin reconciliation skipped: no LITMUS_ADMIN_PASSWORD or AUTHELIA_ADMIN_PASSWORD configured")
        return

    with cluster_session(proxmox_host, master_ip, kubeconfig, kubectl) as session_kubeconfig:
        if run([kubectl, "--kubeconfig", str(session_kubeconfig), "get", "deploy", "litmus-auth-server", "-n", "chaos"], check=False).returncode != 0:
            print("[skip] Litmus admin reconciliation skipped: litmus-auth-server deployment is not present")
            return

        service = kubectl_json(
            kubectl,
            session_kubeconfig,
            ["get", "svc", "litmus-auth-server-service", "-n", "chaos", "-o", "json"],
            context="Unable to read Litmus auth service",
        )
        ports = ((service.get("spec") or {}).get("ports") or [])
        auth_port = None
        for port_spec in ports:
            if not isinstance(port_spec, dict):
                continue
            if port_spec.get("name") == "auth-server":
                auth_port = int(port_spec["port"])
                break
        if auth_port is None and ports:
            first_port = ports[0]
            if isinstance(first_port, dict) and first_port.get("port") is not None:
                auth_port = int(first_port["port"])
        if auth_port is None:
            raise HaaCError("Unable to determine Litmus auth service port")

        mongodb_secret = kubectl_json(
            kubectl,
            session_kubeconfig,
            ["get", "secret", "litmus-mongodb", "-n", "chaos", "-o", "json"],
            context="Unable to read Litmus MongoDB secret",
        )
        mongodb_data = decode_secret_data(mongodb_secret)
        mongodb_root_password = mongodb_data.get("mongodb-root-password")
        if not mongodb_root_password:
            raise HaaCError("Litmus MongoDB root password is missing from secret litmus-mongodb")
        mongo_uri = (
            "mongodb://root:"
            f"{urllib.parse.quote(mongodb_root_password, safe='')}"
            "@127.0.0.1:27017/admin?authSource=admin"
        )

        with kubectl_port_forward(kubectl, session_kubeconfig, "chaos", "svc/litmus-auth-server-service", auth_port) as port:
            status, _ = litmus_login_probe(port, username, password)
        if status not in {200, 401}:
            raise HaaCError(f"Unexpected Litmus login probe status before repair: {status}")
        if status == 401:
            delete_script = f'db.getSiblingDB("auth").users.deleteOne({{username:{json.dumps(username)}}})'
            run(
                [
                    kubectl,
                    "--kubeconfig",
                    str(session_kubeconfig),
                    "exec",
                    "-n",
                    "chaos",
                    "statefulset/litmus-mongodb",
                    "--",
                    "mongosh",
                    "--quiet",
                    mongo_uri,
                    "--eval",
                    delete_script,
                ]
            )
            run([kubectl, "--kubeconfig", str(session_kubeconfig), "rollout", "restart", "deployment/litmus-auth-server", "-n", "chaos"])
            run(
                [
                    kubectl,
                    "--kubeconfig",
                    str(session_kubeconfig),
                    "rollout",
                    "status",
                    "deployment/litmus-auth-server",
                    "-n",
                    "chaos",
                    "--timeout=180s",
                ]
            )
            with kubectl_port_forward(kubectl, session_kubeconfig, "chaos", "svc/litmus-auth-server-service", auth_port) as port:
                status, _ = litmus_login_probe(port, username, password)
            if status != 200:
                raise HaaCError(f"Litmus admin credentials still failed after repair: login probe returned {status}")
            print("[ok] Litmus admin credentials reconciled from the repo-managed secret")
        else:
            print("[ok] Litmus admin credentials already match the repo-managed secret")

        litmus_clear_initial_login(kubectl, session_kubeconfig, mongo_uri, username=username)
        print("[ok] Litmus admin initial-login gate cleared")


def parse_bool(value: str) -> bool:
    return value.strip().lower() in {"1", "true", "yes", "on"}


def load_endpoint_specs(domain_name: str) -> list[dict[str, str]]:
    try:
        return endpointlib.load_endpoint_specs(VALUES_OUTPUT, VALUES_TEMPLATE, domain_name)
    except RuntimeError as exc:
        raise HaaCError(str(exc)) from exc


def probe_web_status(url: str, timeout_seconds: int = 10) -> int:
    return endpointlib.probe_web_status(url, timeout_seconds)


def verify_web(domain_name: str, retries: int = 30, sleep_seconds: int = 10) -> None:
    endpoints = load_endpoint_specs(domain_name)
    results: list[dict[str, str]] = []
    failures: list[dict[str, str]] = []
    auth_url = f"https://auth.{domain_name}"
    last_status_by_url: dict[str, int] = {endpoint["url"]: 0 for endpoint in endpoints}
    last_location_by_url: dict[str, str] = {endpoint["url"]: "" for endpoint in endpoints}
    success_by_url: dict[str, bool] = {endpoint["url"]: False for endpoint in endpoints}

    for attempt in range(retries):
        pending = 0
        for endpoint in endpoints:
            url = endpoint["url"]
            if success_by_url[url]:
                continue
            response = endpointlib.probe_web_response(url)
            status = int(response["status"])
            last_status_by_url[url] = status
            last_location_by_url[url] = str(response.get("location", "") or "")
            if endpointlib.endpoint_verification_success(endpoint, response, auth_url):
                success_by_url[url] = True
            else:
                pending += 1
        if pending == 0:
            break
        if attempt < retries - 1:
            time.sleep(sleep_seconds)

    for endpoint in endpoints:
        url = endpoint["url"]
        success = success_by_url[url]
        result = {
            "service": endpoint["name"],
            "namespace": endpoint["namespace"],
            "url": url,
            "auth": endpoint["auth"],
            "status": str(last_status_by_url[url]),
            "location": last_location_by_url[url],
            "verification": "reachable" if success else "failed",
        }
        results.append(result)
        if not success:
            failures.append(result)

    print("--- Service URL Verification ---")
    print("SERVICE\tNAMESPACE\tAUTH\tSTATUS\tURL")
    for result in results:
        print(
            "\t".join(
                [
                    result["service"],
                    result["namespace"],
                    result["auth"],
                    result["status"],
                    result["url"],
                ]
            )
        )
    print()
    overall = "full-success" if not failures else "partial-failure"
    reachable = len(results) - len(failures)
    print(f"Endpoint verification result: {overall} ({reachable}/{len(results)} reachable)")
    if failures:
        print("Failed endpoints:")
        for result in failures:
            location_suffix = f" -> {result['location']}" if result["location"] else ""
            print(f"- {result['service']} ({result['status']}){location_suffix}: {result['url']}")
    print()
    print(json.dumps({"result": overall, "reachable": reachable, "total": len(results), "endpoints": results}, indent=2))
    if failures:
        raise HaaCError(
            bootstrap_recovery_summary(
                failing_phase="Public URL verification",
                last_verified_phase="Cluster verification",
                rerun_guidance=UP_PHASE_RERUN_GUIDANCE["Public URL verification"],
                detail=f"Endpoint verification incomplete: {len(failures)} of {len(results)} endpoints failed",
            )
        )


def extract_tunnel_id(token: str) -> str:
    padded = token + "=" * ((4 - len(token) % 4) % 4)
    decoded = base64.b64decode(padded.encode("utf-8"))
    payload = json.loads(decoded.decode("utf-8"))
    tunnel_id = payload.get("t")
    if not tunnel_id:
        raise HaaCError("Unable to extract tunnel id from CLOUDFLARE_TUNNEL_TOKEN")
    return tunnel_id


def cloudflare_request(method: str, url: str, token: str, payload: dict | None = None) -> dict:
    data = json.dumps(payload).encode("utf-8") if payload is not None else None
    request = urllib.request.Request(
        url,
        data=data,
        method=method,
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        },
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        body = response.read().decode("utf-8")
    return json.loads(body)


def sync_cloudflare() -> None:
    env = merged_env()
    require_env(
        [
            "CLOUDFLARE_API_TOKEN",
            "CLOUDFLARE_ACCOUNT_ID",
            "CLOUDFLARE_ZONE_ID",
            "CLOUDFLARE_TUNNEL_TOKEN",
            "DOMAIN_NAME",
        ],
        env,
    )

    tunnel_id = extract_tunnel_id(env["CLOUDFLARE_TUNNEL_TOKEN"])
    config_url = f"https://api.cloudflare.com/client/v4/accounts/{env['CLOUDFLARE_ACCOUNT_ID']}/cfd_tunnel/{tunnel_id}/configurations"
    current_config = cloudflare_request("GET", config_url, env["CLOUDFLARE_API_TOKEN"])
    if not current_config.get("success"):
        raise HaaCError(f"Failed to retrieve Cloudflare tunnel configuration: {current_config}")

    config_result = current_config.get("result") or {}
    current_config_payload = config_result.get("config") or {}
    domain_name = env["DOMAIN_NAME"]
    declared_endpoints = load_endpoint_specs(domain_name)
    expected_hostnames = sorted({f"{endpoint['subdomain']}.{domain_name}" for endpoint in declared_endpoints})
    ingress = current_config_payload.get("ingress", [])
    filtered = []
    for item in ingress:
        if item.get("service") == "http_status:404":
            continue
        hostname = str(item.get("hostname") or "")
        if hostname == domain_name or hostname.endswith(f".{domain_name}"):
            continue
        filtered.append(item)
    for hostname in expected_hostnames:
        filtered.append(
            {
                "hostname": hostname,
                "service": "http://traefik.kube-system.svc.cluster.local:80",
                "originRequest": {"noTLSVerify": True},
            }
        )
    filtered.append({"service": "http_status:404"})
    update_payload = {"config": {**current_config_payload, "ingress": filtered}}
    updated = cloudflare_request("PUT", config_url, env["CLOUDFLARE_API_TOKEN"], update_payload)
    if not updated.get("success"):
        raise HaaCError(f"Failed to update Cloudflare tunnel configuration: {updated}")
    print(f"[ok] Cloudflare tunnel ingress reconciled for declared hosts: {', '.join(expected_hostnames)}")

    dns_url = f"https://api.cloudflare.com/client/v4/zones/{env['CLOUDFLARE_ZONE_ID']}/dns_records?per_page=100"
    all_records = cloudflare_request("GET", dns_url, env["CLOUDFLARE_API_TOKEN"])
    if not all_records.get("success"):
        raise HaaCError(f"Failed to retrieve Cloudflare DNS records: {all_records}")

    expected_target = f"{tunnel_id}.cfargotunnel.com"
    managed_domain_records = [
        item
        for item in all_records.get("result", [])
        if item.get("type") in {"A", "AAAA", "CNAME"}
        and item.get("name")
        and (
            item.get("name") == domain_name
            or str(item.get("name")).endswith(f".{domain_name}")
        )
    ]
    for record in managed_domain_records:
        name = str(record.get("name"))
        should_keep = (
            name in expected_hostnames
            and record.get("type") == "CNAME"
            and record.get("content") == expected_target
            and record.get("proxied") is True
        )
        if should_keep:
            continue
        delete_url = f"https://api.cloudflare.com/client/v4/zones/{env['CLOUDFLARE_ZONE_ID']}/dns_records/{record['id']}"
        deleted = cloudflare_request("DELETE", delete_url, env["CLOUDFLARE_API_TOKEN"])
        if not deleted.get("success"):
            raise HaaCError(f"Failed to delete conflicting DNS record {name}: {deleted}")

    existing_names = {
        str(item.get("name"))
        for item in managed_domain_records
        if item.get("type") == "CNAME" and item.get("content") == expected_target and item.get("proxied") is True
    }
    for record_name in expected_hostnames:
        if record_name in existing_names:
            continue
        create_url = f"https://api.cloudflare.com/client/v4/zones/{env['CLOUDFLARE_ZONE_ID']}/dns_records"
        created = cloudflare_request(
            "POST",
            create_url,
            env["CLOUDFLARE_API_TOKEN"],
            {
                "type": "CNAME",
                "name": record_name,
                "content": expected_target,
                "proxied": True,
                "ttl": 1,
            },
        )
        if not created.get("success"):
            raise HaaCError(f"Failed to create DNS record {record_name}: {created}")
    print(f"[ok] Cloudflare DNS reconciled for declared hosts -> {expected_target}")


def restart_cloudflared_rollout(master_ip: str, proxmox_host: str, kubeconfig: Path, kubectl: str) -> None:
    with cluster_session(proxmox_host, master_ip, kubeconfig, kubectl) as session_kubeconfig:
        run(
            [
                kubectl,
                "--kubeconfig",
                str(session_kubeconfig),
                "rollout",
                "restart",
                "deployment/cloudflared",
                "-n",
                "cloudflared",
            ]
        )
        run(
            [
                kubectl,
                "--kubeconfig",
                str(session_kubeconfig),
                "rollout",
                "status",
                "deployment/cloudflared",
                "-n",
                "cloudflared",
                "--timeout=300s",
            ]
        )
        print("[ok] Cloudflared connector rollout completed")


def get_pod_name(kubectl: str, kubeconfig: Path, namespace: str, selector: str) -> str:
    return run_stdout(
        [
            kubectl,
            "--kubeconfig",
            str(kubeconfig),
            "get",
            "pods",
            "-n",
            namespace,
            "-l",
            selector,
            "-o",
            "jsonpath={.items[0].metadata.name}",
        ],
        check=False,
    )


def configure_argocd_local_auth(master_ip: str, proxmox_host: str, kubeconfig: Path, kubectl: str) -> None:
    env = merged_env()
    require_env(["ARGOCD_USERNAME", "ARGOCD_PASSWORD"], env)
    with cluster_session(proxmox_host, master_ip, kubeconfig, kubectl) as session_kubeconfig:
        argocd_pod = get_pod_name(kubectl, session_kubeconfig, "argocd", "app.kubernetes.io/name=argocd-server")
        if not argocd_pod:
            raise HaaCError("ArgoCD server pod not found while configuring local auth")

        bcrypt_hash = run_stdout(
            [
                kubectl,
                "--kubeconfig",
                str(session_kubeconfig),
                "exec",
                "-n",
                "argocd",
                argocd_pod,
                "--",
                "argocd",
                "account",
                "bcrypt",
                "--password",
                env["ARGOCD_PASSWORD"],
            ],
            check=False,
        )
        if not bcrypt_hash:
            raise HaaCError("Unable to generate ArgoCD bcrypt hash from the running server pod")

        timestamp = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        if env["ARGOCD_USERNAME"] == "admin":
            run(
                [
                    kubectl,
                    "--kubeconfig",
                    str(session_kubeconfig),
                    "patch",
                    "secret",
                    "argocd-secret",
                    "-n",
                    "argocd",
                    "-p",
                    json.dumps(
                        {
                            "stringData": {
                                "admin.password": bcrypt_hash,
                                "admin.passwordMtime": timestamp,
                            }
                        }
                    ),
                ]
            )
            return

        run(
            [
                kubectl,
                "--kubeconfig",
                str(session_kubeconfig),
                "patch",
                "cm",
                "argocd-cm",
                "-n",
                "argocd",
                "-p",
                json.dumps({"data": {f"accounts.{env['ARGOCD_USERNAME']}": "login"}}),
            ]
        )
        run(
            [
                kubectl,
                "--kubeconfig",
                str(session_kubeconfig),
                "patch",
                "cm",
                "argocd-rbac-cm",
                "-n",
                "argocd",
                "-p",
                json.dumps({"data": {"policy.csv": f"g, {env['ARGOCD_USERNAME']}, role:admin"}}),
            ]
        )
        run(
            [
                kubectl,
                "--kubeconfig",
                str(session_kubeconfig),
                "patch",
                "secret",
                "argocd-secret",
                "-n",
                "argocd",
                "-p",
                json.dumps(
                    {
                        "stringData": {
                            f"accounts.{env['ARGOCD_USERNAME']}.password": bcrypt_hash,
                            f"accounts.{env['ARGOCD_USERNAME']}.passwordMtime": timestamp,
                        }
                    }
                ),
            ]
        )


def bootstrap_downloaders(master_ip: str, proxmox_host: str, kubeconfig: Path, kubectl: str) -> None:
    env = merged_env()
    require_env(["QUI_PASSWORD"], env)
    qui_password = env["QUI_PASSWORD"]

    with cluster_session(proxmox_host, master_ip, kubeconfig, kubectl) as session_kubeconfig:
        deadline = time.time() + 600
        pod_name = ""
        while time.time() < deadline:
            pod_name = run_stdout(
                [
                    kubectl,
                    "--kubeconfig",
                    str(session_kubeconfig),
                    "get",
                    "pod",
                    "-l",
                    "app=downloaders",
                    "-n",
                    "media",
                    "--sort-by=.metadata.creationTimestamp",
                    "-o",
                    "jsonpath={.items[-1].metadata.name}",
                ],
                check=False,
            )
            if pod_name:
                health = run(
                    [
                        kubectl,
                        "--kubeconfig",
                        str(session_kubeconfig),
                        "exec",
                        "-n",
                        "media",
                        pod_name,
                        "-c",
                        "port-sync",
                        "--",
                        "/bin/sh",
                        "-ec",
                        "curl -fsS http://127.0.0.1:7476/api/auth/me >/dev/null && curl -fsS http://127.0.0.1:8080/api/v2/app/version >/dev/null",
                    ],
                    check=False,
                    capture_output=True,
                )
                if health.returncode == 0:
                    break
            time.sleep(5)
        else:
            raise HaaCError("QUI API did not become available before timeout")

        def exec_port_sync(script: str, *, check: bool = True, capture_output: bool = False) -> subprocess.CompletedProcess[str]:
            return run(
                [
                    kubectl,
                    "--kubeconfig",
                    str(session_kubeconfig),
                    "exec",
                    "-n",
                    "media",
                    pod_name,
                    "-c",
                    "port-sync",
                    "--",
                    "/bin/sh",
                    "-ec",
                    script,
                ],
                check=check,
                capture_output=capture_output,
            )

        qbit_password_q = shlex.quote(qui_password)
        qbit_login_check = (
            f"QBIT_PASSWORD={qbit_password_q}; "
            "login_code=$(curl -sS -o /tmp/qbit-login.txt -w '%{http_code}' "
            "--connect-timeout 5 --max-time 20 "
            "--data-urlencode \"username=admin\" "
            "--data-urlencode \"password=${QBIT_PASSWORD}\" "
            "http://127.0.0.1:8080/api/v2/auth/login || true); "
            "[ \"$login_code\" = \"200\" ] && grep -q 'Ok\\.' /tmp/qbit-login.txt"
        )

        logs = run(
            [
                kubectl,
                "--kubeconfig",
                str(session_kubeconfig),
                "logs",
                "-n",
                "media",
                pod_name,
                "-c",
                "qbittorrent",
            ],
            check=False,
            capture_output=True,
        ).stdout
        temp_password = ""
        for line in logs.splitlines():
            if "A temporary password is provided for this session:" in line:
                temp_password = line.split()[-1]

        if exec_port_sync(qbit_login_check, check=False).returncode != 0:
            if not temp_password:
                raise HaaCError(
                    "qBittorrent is not accepting the desired password and no temporary password was found in container logs."
                )

            exec_port_sync(
                f"TEMP_PASSWORD={shlex.quote(temp_password)}; "
                f"QBIT_PASSWORD={qbit_password_q}; "
                "curl -fsS --connect-timeout 5 --max-time 20 -c /tmp/qbit-cookies.txt "
                "--data-urlencode \"username=admin\" "
                "--data-urlencode \"password=${TEMP_PASSWORD}\" "
                "http://127.0.0.1:8080/api/v2/auth/login >/dev/null && "
                "curl -fsS --connect-timeout 5 --max-time 20 -b /tmp/qbit-cookies.txt "
                "--data-urlencode \"new_password=${QBIT_PASSWORD}\" "
                "http://127.0.0.1:8080/api/v2/auth/changePassword >/dev/null"
            )

        if exec_port_sync(qbit_login_check, check=False).returncode != 0:
            raise HaaCError("qBittorrent did not accept the reconciled password.")

        upsert_instance_script = (
            f"QBIT_PASSWORD={qbit_password_q}; "
            "ESCAPED_QBIT_PASSWORD=$(printf '%s' \"$QBIT_PASSWORD\" | sed 's/\\\\/\\\\\\\\/g; s/\"/\\\\\"/g'); "
            "extract_instance_id() { "
            "compact=\"$1\"; "
            "instance_id=$(printf '%s' \"$compact\" | sed -n 's/.*\"id\":\\([0-9][0-9]*\\),\"name\":\"qBittorrent\".*/\\1/p'); "
            "if [ -z \"$instance_id\" ]; then "
            "instance_id=$(printf '%s' \"$compact\" | sed -n 's/.*\"name\":\"qBittorrent\",\"id\":\\([0-9][0-9]*\\).*/\\1/p'); "
            "fi; "
            "printf '%s' \"$instance_id\"; "
            "}; "
            "INSTANCE_PAYLOAD=$(printf '{\"name\":\"qBittorrent\",\"host\":\"http://127.0.0.1:8080\",\"username\":\"admin\",\"password\":\"%s\",\"hasLocalFilesystemAccess\":true}' \"$ESCAPED_QBIT_PASSWORD\"); "
            "INSTANCES=$(curl -fsS --connect-timeout 5 --max-time 20 http://127.0.0.1:7476/api/instances); "
            "INSTANCES_COMPACT=$(printf '%s' \"$INSTANCES\" | tr -d '\\n '); "
            "INSTANCE_ID=$(extract_instance_id \"$INSTANCES_COMPACT\"); "
            "if [ -n \"$INSTANCE_ID\" ]; then "
            "curl -fsS --connect-timeout 5 --max-time 20 -X PUT -H 'Content-Type: application/json' --data \"$INSTANCE_PAYLOAD\" "
            "\"http://127.0.0.1:7476/api/instances/${INSTANCE_ID}\" >/dev/null; "
            "else "
            "CREATE_CODE=$(curl -sS --connect-timeout 5 --max-time 20 -o /tmp/qui-instance-create.json -w '%{http_code}' -H 'Content-Type: application/json' "
            "--data \"$INSTANCE_PAYLOAD\" http://127.0.0.1:7476/api/instances || true); "
            "if [ \"$CREATE_CODE\" != \"200\" ] && [ \"$CREATE_CODE\" != \"201\" ]; then "
            "cat /tmp/qui-instance-create.json >&2; exit 1; "
            "fi; "
            "INSTANCES=$(curl -fsS --connect-timeout 5 --max-time 20 http://127.0.0.1:7476/api/instances); "
            "INSTANCES_COMPACT=$(printf '%s' \"$INSTANCES\" | tr -d '\\n '); "
            "INSTANCE_ID=$(extract_instance_id \"$INSTANCES_COMPACT\"); "
            "fi; "
            "[ -n \"$INSTANCE_ID\" ]; "
            "TEST_RESPONSE=''; "
            "for _ in $(seq 1 24); do "
            "TEST_RESPONSE=$(curl -sS --connect-timeout 5 --max-time 20 -X POST \"http://127.0.0.1:7476/api/instances/${INSTANCE_ID}/test\" || true); "
            "if printf '%s' \"$TEST_RESPONSE\" | grep -q '\"connected\":true'; then exit 0; fi; "
            "sleep 5; "
            "done; "
            "printf '%s\\n' \"$TEST_RESPONSE\" >&2; "
            "exit 1"
        )
        exec_port_sync(upsert_instance_script)


def tofu_output_json(tofu_dir: Path) -> dict:
    tofu_binary = resolved_binary("tofu")
    try:
        completed = run(
            [tofu_binary, f"-chdir={tofu_dir}", "output", "-json", "-no-color"],
            check=False,
            capture_output=True,
        )
    except FileNotFoundError:
        return {}
    if completed.returncode != 0:
        return {}
    output = (completed.stdout or "").strip()
    if not output.startswith("{"):
        return {}
    try:
        return json.loads(output) if output else {}
    except json.JSONDecodeError:
        return {}


def tofu_output_value(tofu_dir: Path, name: str, default: str = "") -> str:
    outputs = tofu_output_json(tofu_dir)
    item = outputs.get(name)
    if not isinstance(item, dict) or "value" not in item:
        return default
    value = item["value"]
    if value is None:
        return default
    if isinstance(value, str):
        return value.strip() or default
    if isinstance(value, (int, float, bool)):
        return str(value)
    return json.dumps(value, separators=(",", ":"))


def shutdown_cluster(proxmox_host: str, tofu_dir: Path) -> None:
    outputs = tofu_output_json(tofu_dir)
    master_vmid = outputs.get("master_vmid", {}).get("value")
    worker_items = outputs.get("workers", {}).get("value", {})

    vmids: list[tuple[str, str]] = []
    if isinstance(master_vmid, int):
        vmids.append((str(master_vmid), "Master"))
    if isinstance(worker_items, dict):
        for index, worker in enumerate(worker_items.values(), start=1):
            vmid = worker.get("vmid")
            if isinstance(vmid, int):
                vmids.append((str(vmid), f"Worker {index}"))

    for vmid, label in vmids:
        status = run_proxmox_ssh(
            proxmox_host,
            f"pct status {vmid}",
            check=False,
            capture_output=True,
        )
        if "status: running" not in (status.stdout or ""):
            continue
        run_proxmox_ssh(
            proxmox_host,
            f"pct exec {vmid} -- bash -lc 'systemctl stop k3s 2>/dev/null || true; systemctl stop k3s-agent 2>/dev/null || true'",
            check=False,
        )
        graceful = run_proxmox_ssh(proxmox_host, f"pct shutdown {vmid} --timeout 180", check=False)
        if graceful.returncode != 0:
            run_proxmox_ssh(proxmox_host, f"pct stop {vmid}", check=False)
        print(f"Shutdown requested for {label} ({vmid})")


def restore_k3s(proxmox_host: str, tofu_dir: Path, backup_file: str, nas_mount_path: str) -> None:
    master_vmid = run_stdout([resolved_binary("tofu"), f"-chdir={tofu_dir}", "output", "-raw", "master_vmid"])
    run_proxmox_ssh(proxmox_host, f"pct exec {master_vmid} -- systemctl stop k3s")

    restore_script = f"""
set -e
LXC_ID={shlex.quote(master_vmid)}
pct exec "$LXC_ID" -- mv /var/lib/rancher/k3s/server/db/state.db /var/lib/rancher/k3s/server/db/state.db.corrupted-$(date +%s) || true
cp {shlex.quote(nas_mount_path)}/{shlex.quote(backup_file)} /var/lib/lxc/$LXC_ID/rootfs/var/lib/rancher/k3s/server/db/state.db
pct exec "$LXC_ID" -- chown root:root /var/lib/rancher/k3s/server/db/state.db
"""
    run_proxmox_ssh(proxmox_host, f"bash -lc {shlex.quote(restore_script)}")
    run_proxmox_ssh(proxmox_host, f"pct exec {master_vmid} -- systemctl start k3s")


def remove_file(path: Path) -> None:
    if path.exists():
        path.unlink()


def clean_local_artifacts() -> None:
    removed: list[str] = []
    for artifact_dir in LEGACY_ARTIFACT_DIRS:
        if artifact_dir.exists():
            shutil.rmtree(artifact_dir, ignore_errors=True)
            removed.append(str(artifact_dir.relative_to(ROOT)))

    for pattern in LEGACY_ARTIFACT_PATTERNS:
        for path in ROOT.glob(pattern):
            if path.is_file():
                path.unlink(missing_ok=True)
                removed.append(str(path.relative_to(ROOT)))

    if removed:
        print("[ok] Removed local investigation artifacts:")
        for item in sorted(removed):
            print(f"  - {item}")
    else:
        print("[ok] No stray local investigation artifacts were found outside .tmp/")


def monitor(master_ip: str, proxmox_host: str, kubeconfig: Path) -> None:
    k9s = shutil.which("k9s")
    if not k9s:
        raise HaaCError("k9s is not installed or not on PATH.")
    with cluster_session(proxmox_host, master_ip, kubeconfig, resolved_binary("kubectl")) as session_kubeconfig:
        subprocess.run([k9s, "--all-namespaces", "--kubeconfig", str(session_kubeconfig)], cwd=str(ROOT), check=False)


def ensure_repo_ssh_keypair() -> None:
    if SSH_PRIVATE_KEY_PATH.exists() and SSH_PUBLIC_KEY_PATH.exists():
        return
    if shutil.which("ssh-keygen") is None:
        raise HaaCError("ssh-keygen is required to create the repository SSH keypair.")
    SSH_DIR.mkdir(parents=True, exist_ok=True)
    run(
        [
            "ssh-keygen",
            "-t",
            "ed25519",
            "-f",
            str(SSH_PRIVATE_KEY_PATH),
            "-N",
            "",
            "-C",
            "haac@local",
        ]
    )


def ensure_semaphore_ssh_keypair() -> None:
    if SEMAPHORE_SSH_PRIVATE_KEY_PATH.exists() and SEMAPHORE_SSH_PUBLIC_KEY_PATH.exists():
        return
    if shutil.which("ssh-keygen") is None:
        raise HaaCError("ssh-keygen is required to create the Semaphore SSH keypair.")
    SSH_DIR.mkdir(parents=True, exist_ok=True)
    run(
        [
            "ssh-keygen",
            "-t",
            "ed25519",
            "-f",
            str(SEMAPHORE_SSH_PRIVATE_KEY_PATH),
            "-N",
            "",
            "-C",
            "haac-semaphore@local",
        ]
    )


def ensure_repo_deploy_ssh_keypair() -> None:
    if REPO_DEPLOY_SSH_PRIVATE_KEY_PATH.exists() and REPO_DEPLOY_SSH_PUBLIC_KEY_PATH.exists():
        return
    if shutil.which("ssh-keygen") is None:
        raise HaaCError("ssh-keygen is required to create the repository deploy SSH keypair.")
    SSH_DIR.mkdir(parents=True, exist_ok=True)
    run(
        [
            "ssh-keygen",
            "-t",
            "ed25519",
            "-f",
            str(REPO_DEPLOY_SSH_PRIVATE_KEY_PATH),
            "-N",
            "",
            "-C",
            "haac-repo-deploy@local",
        ]
    )


def doctor() -> None:
    env = merged_env()
    failures: list[str] = []
    ensure_repo_ssh_keypair()
    ensure_repo_deploy_ssh_keypair()
    known_hosts_path(env)
    checks = [
        ("python", "python"),
        ("git", "git"),
        ("ssh", "ssh"),
        ("node", "node"),
        ("kubectl", "kubectl"),
        ("task", "task"),
        ("tofu", "tofu"),
        ("helm", "helm"),
        ("kubeseal", "kubeseal"),
    ]
    if is_windows():
        checks.extend(
            [
                ("wsl", "wsl"),
            ]
        )
    else:
        checks.append(("ansible-playbook", "ansible-playbook"))

    for label, binary in checks:
        location = tool_location(binary)
        if location:
            print(f"[ok] {label}: {location}")
        else:
            print(f"[missing] {label}")
            failures.append(label)

    if SSH_PRIVATE_KEY_PATH.exists() and SSH_PUBLIC_KEY_PATH.exists():
        print(f"[ok] repo ssh keypair: {SSH_PRIVATE_KEY_PATH}")
    else:
        print(f"[missing] repo ssh keypair: {SSH_PRIVATE_KEY_PATH}")
        failures.append("repo-ssh-keypair")

    if SEMAPHORE_SSH_PRIVATE_KEY_PATH.exists() and SEMAPHORE_SSH_PUBLIC_KEY_PATH.exists():
        print(f"[ok] semaphore maintenance ssh keypair: {SEMAPHORE_SSH_PRIVATE_KEY_PATH}")
    else:
        print(
            f"[warn] semaphore maintenance ssh keypair missing: {SEMAPHORE_SSH_PRIVATE_KEY_PATH} "
            "(it will be created during `configure-os` or `task up` before cluster publication)"
        )

    if REPO_DEPLOY_SSH_PRIVATE_KEY_PATH.exists() and REPO_DEPLOY_SSH_PUBLIC_KEY_PATH.exists():
        print(f"[ok] repo deploy ssh keypair: {REPO_DEPLOY_SSH_PRIVATE_KEY_PATH}")
    else:
        print(f"[missing] repo deploy ssh keypair: {REPO_DEPLOY_SSH_PRIVATE_KEY_PATH}")
        failures.append("repo-deploy-ssh-keypair")

    print(f"[ok] known_hosts path: {known_hosts_path(env)}")

    if is_windows():
        distro = wsl_distro(env)
        distro_check = run(["wsl", "-l", "-q"], check=False, capture_output=True)
        available_distros = {
            line.strip().replace("\x00", "")
            for line in (distro_check.stdout or "").splitlines()
            if line.strip()
        }
        if distro not in available_distros:
            print(f"[missing] wsl distro: {distro}")
            failures.append(f"wsl-distro:{distro}")
        else:
            print(f"[ok] wsl distro: {distro}")
            linux_arch = wsl_arch(env)
            for binary in ("tofu", "helm", "kubectl", "kubeseal", "task"):
                linux_tool = local_binary_path(binary, "linux", linux_arch)
                if linux_tool.exists():
                    print(f"[ok] portable linux tool ({binary}): {linux_tool}")
                else:
                    print(f"[missing] portable linux tool ({binary})")
                    failures.append(f"portable-linux:{binary}")
            for label, command in (
                ("ansible-playbook", "command -v ansible-playbook"),
                ("git", "command -v git"),
                ("python3", "command -v python3"),
                ("ssh", "command -v ssh"),
                ("sshpass", "command -v sshpass"),
            ):
                completed = run(
                    wsl_command("bash", "-lc", command, distro=distro),
                    check=False,
                    capture_output=True,
                )
                if completed.returncode == 0 and completed.stdout.strip():
                    print(f"[ok] {distro}:{label}: {completed.stdout.strip()}")
                else:
                    print(f"[missing] {distro}:{label}")
                    failures.append(f"{distro}:{label}")

    if failures:
        raise HaaCError(f"Missing required tooling: {', '.join(failures)}")


def cleanup_legacy_tools_layout() -> None:
    if LEGACY_TOOLS_BIN_DIR.exists():
        shutil.rmtree(LEGACY_TOOLS_BIN_DIR)
    LEGACY_TOOLS_METADATA_PATH.unlink(missing_ok=True)


def wsl_distro_exists(env: dict[str, str]) -> bool:
    if shutil.which("wsl") is None:
        return False
    distro = wsl_distro(env)
    distro_check = run(["wsl", "-l", "-q"], check=False, capture_output=True)
    available_distros = {
        line.strip().replace("\x00", "")
        for line in (distro_check.stdout or "").splitlines()
        if line.strip()
    }
    return distro in available_distros


def wsl_arch(env: dict[str, str]) -> str:
    completed = run(
        wsl_command("bash", "-lc", "uname -m", distro=wsl_distro(env)),
        check=False,
        capture_output=True,
    )
    if completed.returncode != 0 or not completed.stdout.strip():
        return host_arch()
    machine = completed.stdout.strip().lower()
    arch_map = {
        "x86_64": "amd64",
        "amd64": "amd64",
        "arm64": "arm64",
        "aarch64": "arm64",
    }
    return arch_map.get(machine, host_arch())


def install_wsl_tools() -> None:
    if not is_windows():
        raise HaaCError("install-wsl-tools is supported only on Windows.")
    if shutil.which("wsl") is None:
        raise HaaCError("WSL is not installed. Install WSL and Debian first, then rerun this command.")

    env = merged_env()
    distro = wsl_distro(env)
    if not wsl_distro_exists(env):
        raise HaaCError(f"WSL distro '{distro}' was not found. Install it first, then rerun this command.")

    print(f"Installing WSL packages in {distro}...")
    run(
        wsl_command(
            "bash",
            "-lc",
            "apt-get update && DEBIAN_FRONTEND=noninteractive apt-get install -y ansible git python3 openssh-client sshpass",
            distro=distro,
            user="root",
        )
    )


def install_tools() -> None:
    env = merged_env()
    targets = [(host_platform(), host_arch())]
    if is_windows():
        targets.append(("linux", wsl_arch(env)))

    seen_targets: set[tuple[str, str]] = set()
    for platform_name, arch in targets:
        if (platform_name, arch) in seen_targets:
            continue
        seen_targets.add((platform_name, arch))
        for binary in ("tofu", "helm", "kubectl", "kubeseal", "task"):
            installed = ensure_local_cli_tool(binary, platform_name, arch)
            print(f"Installed portable {binary} for {platform_name}-{arch} at {installed}")

    cleanup_legacy_tools_layout()

    missing_global = [binary for binary in ("python", "git", "ssh") if tool_location(binary) is None]
    if missing_global:
        raise HaaCError(
            "Missing required global tooling that is not bootstrapped locally: " + ", ".join(missing_global)
        )

    ensure_repo_ssh_keypair()
    ensure_semaphore_ssh_keypair()
    ensure_repo_deploy_ssh_keypair()

    if is_windows():
        install_wsl_tools()


def cmd_check_env(_: argparse.Namespace) -> None:
    env = merged_env()
    if not ENV_FILE.exists():
        raise HaaCError("Please create a .env file based on .env.example")
    require_env(
        [
            "LXC_PASSWORD",
            "LXC_MASTER_HOSTNAME",
            "DOMAIN_NAME",
            "NAS_ADDRESS",
            "HOST_NAS_PATH",
            "NAS_PATH",
            "NAS_SHARE_NAME",
            "SMB_USER",
            "SMB_PASSWORD",
            "STORAGE_UID",
            "STORAGE_GID",
            "GITOPS_REPO_URL",
            "GITOPS_REPO_REVISION",
            "CLOUDFLARE_API_TOKEN",
            "CLOUDFLARE_ACCOUNT_ID",
            "CLOUDFLARE_ZONE_ID",
            "CLOUDFLARE_TUNNEL_TOKEN",
        ],
        env,
    )
    gitopslib.validate_falco_runtime_inputs(env)
    access_host = proxmox_access_host(env)
    access_hint = (
        "Set PROXMOX_ACCESS_HOST to the workstation-reachable Proxmox IP/FQDN, "
        "or ensure MASTER_TARGET_NODE resolves locally before running `task up`."
    )
    ensure_tcp_endpoint(access_host, 8006, label="Proxmox API", hint=access_hint)
    ensure_tcp_endpoint(access_host, 22, label="Proxmox SSH", hint=access_hint)


def cmd_kubeconfig_path(_: argparse.Namespace) -> None:
    print(local_kubeconfig_path())


def cmd_proxmox_access_host(_: argparse.Namespace) -> None:
    print(proxmox_access_host(merged_env()))


def cmd_tool_path(args: argparse.Namespace) -> None:
    if args.name in bootstrappable_tools():
        print(ensure_local_cli_tool(args.name))
        return
    print(resolved_binary(args.name))


def cmd_doctor(_: argparse.Namespace) -> None:
    doctor()
    print(
        "Doctor checks local tooling only. Run `python scripts/haac.py check-env` "
        "before `task up` to verify workstation-to-Proxmox reachability."
    )


def cmd_install_windows_tools(_: argparse.Namespace) -> None:
    install_tools()


def cmd_install_tools(_: argparse.Namespace) -> None:
    install_tools()


def cmd_install_wsl_tools(_: argparse.Namespace) -> None:
    install_wsl_tools()


def resolve_default_gateway(env: dict[str, str]) -> str:
    if env.get("LXC_GATEWAY"):
        return env["LXC_GATEWAY"]
    host = proxmox_access_host(env)
    completed = run_proxmox_ssh(
        host,
        "ip route | awk '/default/ {print $3; exit}'",
        connect_timeout=5,
        check=False,
        capture_output=True,
    )
    if completed.returncode == 0:
        output = completed.stdout.strip()
        if output:
            via_match = re.search(r"\bvia\s+((?:\d{1,3}\.){3}\d{1,3})\b", output)
            if via_match:
                return via_match.group(1)
            ip_match = re.search(r"\b(?:\d{1,3}\.){3}\d{1,3}\b", output)
            if ip_match:
                return ip_match.group(0)
            return output
    return ""


def tofu_tf_vars(env: dict[str, str]) -> dict[str, str]:
    direct_env_map = {
        "lxc_password": "LXC_PASSWORD",
        "lxc_rootfs_datastore": "LXC_ROOTFS_DATASTORE",
        "lxc_master_hostname": "LXC_MASTER_HOSTNAME",
        "lxc_unprivileged": "LXC_UNPRIVILEGED",
        "lxc_nesting": "LXC_NESTING",
        "master_target_node": "MASTER_TARGET_NODE",
        "k3s_master_ip": "K3S_MASTER_IP",
        "worker_nodes": "WORKER_NODES_JSON",
        "host_nas_path": "HOST_NAS_PATH",
        "cloudflare_tunnel_token": "CLOUDFLARE_TUNNEL_TOKEN",
        "domain_name": "DOMAIN_NAME",
        "protonvpn_openvpn_username": "PROTONVPN_OPENVPN_USERNAME",
        "protonvpn_openvpn_password": "PROTONVPN_OPENVPN_PASSWORD",
        "smb_user": "SMB_USER",
        "smb_password": "SMB_PASSWORD",
        "nas_address": "NAS_ADDRESS",
        "nas_share_name": "NAS_SHARE_NAME",
        "storage_uid": "STORAGE_UID",
        "storage_gid": "STORAGE_GID",
    }
    mapped = {f"TF_VAR_{tf_var}": env.get(env_key, "") for tf_var, env_key in direct_env_map.items()}
    mapped["TF_VAR_proxmox_access_host"] = proxmox_access_host(env)
    mapped["TF_VAR_lxc_gateway"] = resolve_default_gateway(env)
    mapped["TF_VAR_python_executable"] = env.get("PYTHON_CMD", "python")
    mapped["TF_VAR_maintenance_ssh_user"] = maintenance_user(env)
    return mapped


def tofu_cli_env() -> dict[str, str]:
    env = merged_env()
    mapped = os.environ.copy()
    mapped.update(tofu_tf_vars(env))
    return mapped


def tofu_state_addresses(tofu_dir: Path, env: dict[str, str], tofu_binary: str) -> set[str]:
    completed = subprocess.run(
        [tofu_binary, f"-chdir={tofu_dir}", "state", "list"],
        cwd=str(ROOT),
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )
    if completed.returncode != 0:
        return set()
    return {line.strip() for line in completed.stdout.splitlines() if line.strip()}


def tofu_state_resource_id(tofu_dir: Path, env: dict[str, str], tofu_binary: str, address: str) -> str:
    completed = subprocess.run(
        [tofu_binary, f"-chdir={tofu_dir}", "state", "show", address],
        cwd=str(ROOT),
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )
    if completed.returncode != 0:
        raise HaaCError(f"Unable to inspect legacy OpenTofu state for {address}")
    match = re.search(r'^\s*id\s*=\s*"?(?P<id>[^"\r\n]+)"?\s*$', completed.stdout, re.MULTILINE)
    if not match:
        raise HaaCError(f"Unable to extract resource id from legacy OpenTofu state for {address}")
    return match.group("id")


def migrate_legacy_proxmox_download_file_state(tofu_dir: Path, env: dict[str, str], tofu_binary: str) -> None:
    addresses = tofu_state_addresses(tofu_dir, env, tofu_binary)
    if LEGACY_PROXMOX_DOWNLOAD_FILE_ADDRESS not in addresses:
        return

    if PROXMOX_DOWNLOAD_FILE_ADDRESS not in addresses:
        resource_id = tofu_state_resource_id(tofu_dir, env, tofu_binary, LEGACY_PROXMOX_DOWNLOAD_FILE_ADDRESS)
        print(
            "Migrating legacy Proxmox download-file state to "
            f"{PROXMOX_DOWNLOAD_FILE_ADDRESS} before plan/apply..."
        )
        run([tofu_binary, f"-chdir={tofu_dir}", "import", PROXMOX_DOWNLOAD_FILE_ADDRESS, resource_id], env=env)

    print(f"Removing legacy OpenTofu state entry {LEGACY_PROXMOX_DOWNLOAD_FILE_ADDRESS}...")
    run([tofu_binary, f"-chdir={tofu_dir}", "state", "rm", LEGACY_PROXMOX_DOWNLOAD_FILE_ADDRESS], env=env)


def run_tofu_command(tofu_dir: Path, arguments: list[str]) -> None:
    tofu_binary = resolved_binary("tofu")
    env = tofu_cli_env()
    if arguments and arguments[0] in {"plan", "apply"}:
        migrate_legacy_proxmox_download_file_state(tofu_dir, env, tofu_binary)
    run([tofu_binary, f"-chdir={tofu_dir}", *arguments], env=env)


def cmd_default_gateway(_: argparse.Namespace) -> None:
    print(resolve_default_gateway(merged_env()))


def cmd_env_value(args: argparse.Namespace) -> None:
    env = merged_env()
    value = env.get(args.name, args.default)
    if value is None:
        raise HaaCError(f"Environment value not found: {args.name}")
    print(value)


def cmd_tofu_output(args: argparse.Namespace) -> None:
    print(tofu_output_value(Path(args.dir), args.name, args.default))


def cmd_sync_repo(args: argparse.Namespace) -> None:
    sync_repo()


def cmd_setup_hooks(_: argparse.Namespace) -> None:
    install_hooks()


def cmd_pre_commit_hook(_: argparse.Namespace) -> None:
    pre_commit_hook()


def cmd_run_ansible(args: argparse.Namespace) -> None:
    env = merged_env()
    ensure_semaphore_ssh_keypair()
    inventory = ROOT / args.inventory
    playbook = ROOT / args.playbook
    extra_args = shlex.split(args.extra_args) if args.extra_args else []
    if is_windows():
        run_ansible_wsl(inventory, playbook, extra_args, env)
        return

    env["HAAC_KUBECONFIG_PATH"] = str(local_kubeconfig_path())
    env["HAAC_SSH_PRIVATE_KEY_PATH"] = str(SSH_PRIVATE_KEY_PATH)
    env["HAAC_SSH_KNOWN_HOSTS_PATH"] = str(known_hosts_path(env))
    env["HAAC_SSH_HOST_KEY_CHECKING"] = ssh_host_key_checking_mode(env)
    env["HAAC_PROXMOX_ACCESS_HOST"] = proxmox_access_host(env)
    ensure_parent(local_kubeconfig_path())
    run(["ansible-playbook", *extra_args, "-i", str(inventory), str(playbook)], env=env)


def cmd_generate_secrets(args: argparse.Namespace) -> None:
    kubeconfig = Path(args.kubeconfig)
    with cluster_session(args.proxmox_host, args.master_ip, kubeconfig, args.kubectl) as session_kubeconfig:
        generate_secrets_core(session_kubeconfig, args.kubectl, fetch_cert=True)
        upload_inventory_configmap(args.kubectl, session_kubeconfig)


def cmd_generate_secrets_local(args: argparse.Namespace) -> None:
    generate_secrets_core(Path(args.kubeconfig), args.kubectl, fetch_cert=False)


def cmd_push_changes(args: argparse.Namespace) -> None:
    push_changes(args.push_all, args.kubectl, Path(args.kubeconfig))


def cmd_deploy_argocd(args: argparse.Namespace) -> None:
    deploy_argocd(args.master_ip, args.proxmox_host, Path(args.kubeconfig), args.kubectl)


def cmd_deploy_local(args: argparse.Namespace) -> None:
    deploy_local(args.master_ip, args.proxmox_host, Path(args.kubeconfig), args.kubectl, args.helm)


def cmd_wait_for_stack(args: argparse.Namespace) -> None:
    wait_for_stack(args.master_ip, args.proxmox_host, Path(args.kubeconfig), args.kubectl, args.timeout)


def cmd_verify_cluster(args: argparse.Namespace) -> None:
    verify_cluster(args.master_ip, args.proxmox_host, Path(args.kubeconfig), args.kubectl)


def cmd_reconcile_litmus_admin(args: argparse.Namespace) -> None:
    reconcile_litmus_admin(args.master_ip, args.proxmox_host, Path(args.kubeconfig), args.kubectl)


def cmd_reconcile_litmus_chaos(args: argparse.Namespace) -> None:
    reconcile_litmus_chaos(args.master_ip, args.proxmox_host, Path(args.kubeconfig), args.kubectl)


def cmd_verify_web(args: argparse.Namespace) -> None:
    verify_web(args.domain)


def cmd_sync_cloudflare(args: argparse.Namespace) -> None:
    sync_cloudflare()
    if args.master_ip and args.proxmox_host and args.kubeconfig and args.kubectl:
        restart_cloudflared_rollout(args.master_ip, args.proxmox_host, Path(args.kubeconfig), args.kubectl)


def cmd_configure_apps(args: argparse.Namespace) -> None:
    bootstrap_downloaders(args.master_ip, args.proxmox_host, Path(args.kubeconfig), args.kubectl)


def cmd_configure_argocd_local_auth(args: argparse.Namespace) -> None:
    configure_argocd_local_auth(args.master_ip, args.proxmox_host, Path(args.kubeconfig), args.kubectl)


def cmd_restore_k3s(args: argparse.Namespace) -> None:
    restore_k3s(args.proxmox_host, Path(args.tofu_dir), args.backup_file, args.nas_mount_path)


def cmd_shutdown_cluster(args: argparse.Namespace) -> None:
    shutdown_cluster(args.proxmox_host, Path(args.tofu_dir))


def cmd_remove_file(args: argparse.Namespace) -> None:
    remove_file(Path(args.path))


def cmd_clean_artifacts(_: argparse.Namespace) -> None:
    clean_local_artifacts()


def cmd_monitor(args: argparse.Namespace) -> None:
    monitor(args.master_ip, args.proxmox_host, Path(args.kubeconfig))


def cmd_task_run(args: argparse.Namespace) -> None:
    task_args = list(args.task_args)
    if task_args and task_args[0] == "--":
        task_args = task_args[1:]
    if not task_args:
        raise HaaCError("Please pass the task arguments after `--`, for example: task-run -- up")
    task_binary = ensure_local_cli_tool("task")
    env = os.environ.copy()
    env["PATH"] = os.pathsep.join([str(local_binary_path("task").parent), env.get("PATH", "")])
    if "up" in task_args:
        returncode, output_lines = run_task_with_output(task_binary, task_args, env)
        if returncode != 0:
            emit_up_failure_summary(output_lines)
            raise HaaCError(f"Task command failed with exit code {returncode}")
        return

    completed = subprocess.run([task_binary, *task_args], cwd=str(ROOT), env=env, check=False)
    if completed.returncode != 0:
        raise HaaCError(f"Task command failed with exit code {completed.returncode}")


def cmd_run_tofu(args: argparse.Namespace) -> None:
    run_tofu_command(Path(args.dir), list(args.tofu_args))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Cross-platform orchestration helpers for HaaC")
    subparsers = parser.add_subparsers(dest="command", required=True)

    command = subparsers.add_parser("check-env")
    command.set_defaults(func=cmd_check_env)

    command = subparsers.add_parser("doctor")
    command.set_defaults(func=cmd_doctor)

    command = subparsers.add_parser("install-tools")
    command.set_defaults(func=cmd_install_tools)

    command = subparsers.add_parser("install-windows-tools")
    command.set_defaults(func=cmd_install_windows_tools)

    command = subparsers.add_parser("install-wsl-tools")
    command.set_defaults(func=cmd_install_wsl_tools)

    command = subparsers.add_parser("kubeconfig-path")
    command.set_defaults(func=cmd_kubeconfig_path)

    command = subparsers.add_parser("proxmox-access-host")
    command.set_defaults(func=cmd_proxmox_access_host)

    command = subparsers.add_parser("tool-path")
    command.add_argument(
        "--name",
        required=True,
        choices=["tofu", "helm", "kubectl", "kubeseal", "git", "ssh", "python", "task"],
    )
    command.set_defaults(func=cmd_tool_path)

    command = subparsers.add_parser("default-gateway")
    command.set_defaults(func=cmd_default_gateway)

    command = subparsers.add_parser("env-value")
    command.add_argument("--name", required=True)
    command.add_argument("--default", default="")
    command.set_defaults(func=cmd_env_value)

    command = subparsers.add_parser("tofu-output")
    command.add_argument("--dir", required=True)
    command.add_argument("--name", required=True)
    command.add_argument("--default", default="")
    command.set_defaults(func=cmd_tofu_output)

    command = subparsers.add_parser("sync-repo")
    command.set_defaults(func=cmd_sync_repo)

    command = subparsers.add_parser("setup-hooks")
    command.set_defaults(func=cmd_setup_hooks)

    command = subparsers.add_parser("pre-commit-hook")
    command.set_defaults(func=cmd_pre_commit_hook)

    command = subparsers.add_parser("run-ansible")
    command.add_argument("--inventory", required=True)
    command.add_argument("--playbook", required=True)
    command.add_argument("--extra-args", default="")
    command.set_defaults(func=cmd_run_ansible)

    command = subparsers.add_parser("generate-secrets")
    command.add_argument("--master-ip", required=True)
    command.add_argument("--proxmox-host", required=True)
    command.add_argument("--kubeconfig", required=True)
    command.add_argument("--kubectl", default="kubectl")
    command.set_defaults(func=cmd_generate_secrets)

    command = subparsers.add_parser("generate-secrets-local")
    command.add_argument("--kubeconfig", required=True)
    command.add_argument("--kubectl", default="kubectl")
    command.set_defaults(func=cmd_generate_secrets_local)

    command = subparsers.add_parser("push-changes")
    command.add_argument("--push-all", action="store_true")
    command.add_argument("--kubeconfig", required=True)
    command.add_argument("--kubectl", default="kubectl")
    command.set_defaults(func=cmd_push_changes)

    command = subparsers.add_parser("deploy-argocd")
    command.add_argument("--master-ip", required=True)
    command.add_argument("--proxmox-host", required=True)
    command.add_argument("--kubeconfig", required=True)
    command.add_argument("--kubectl", default="kubectl")
    command.set_defaults(func=cmd_deploy_argocd)

    command = subparsers.add_parser("deploy-local")
    command.add_argument("--master-ip", required=True)
    command.add_argument("--proxmox-host", required=True)
    command.add_argument("--kubeconfig", required=True)
    command.add_argument("--kubectl", default="kubectl")
    command.add_argument("--helm", default="helm")
    command.set_defaults(func=cmd_deploy_local)

    command = subparsers.add_parser("wait-for-stack")
    command.add_argument("--master-ip", required=True)
    command.add_argument("--proxmox-host", required=True)
    command.add_argument("--kubeconfig", required=True)
    command.add_argument("--kubectl", default="kubectl")
    command.add_argument("--timeout", type=int, default=3600)
    command.set_defaults(func=cmd_wait_for_stack)

    command = subparsers.add_parser("verify-cluster")
    command.add_argument("--master-ip", required=True)
    command.add_argument("--proxmox-host", required=True)
    command.add_argument("--kubeconfig", required=True)
    command.add_argument("--kubectl", default="kubectl")
    command.set_defaults(func=cmd_verify_cluster)

    command = subparsers.add_parser("reconcile-litmus-admin")
    command.add_argument("--master-ip", required=True)
    command.add_argument("--proxmox-host", required=True)
    command.add_argument("--kubeconfig", required=True)
    command.add_argument("--kubectl", default="kubectl")
    command.set_defaults(func=cmd_reconcile_litmus_admin)

    command = subparsers.add_parser("reconcile-litmus-chaos")
    command.add_argument("--master-ip", required=True)
    command.add_argument("--proxmox-host", required=True)
    command.add_argument("--kubeconfig", required=True)
    command.add_argument("--kubectl", default="kubectl")
    command.set_defaults(func=cmd_reconcile_litmus_chaos)

    command = subparsers.add_parser("verify-web")
    command.add_argument("--domain", required=True)
    command.set_defaults(func=cmd_verify_web)

    command = subparsers.add_parser("sync-cloudflare")
    command.add_argument("--master-ip")
    command.add_argument("--proxmox-host")
    command.add_argument("--kubeconfig")
    command.add_argument("--kubectl")
    command.set_defaults(func=cmd_sync_cloudflare)

    command = subparsers.add_parser("configure-apps")
    command.add_argument("--master-ip", required=True)
    command.add_argument("--proxmox-host", required=True)
    command.add_argument("--kubeconfig", required=True)
    command.add_argument("--kubectl", default="kubectl")
    command.set_defaults(func=cmd_configure_apps)

    command = subparsers.add_parser("configure-argocd-local-auth")
    command.add_argument("--master-ip", required=True)
    command.add_argument("--proxmox-host", required=True)
    command.add_argument("--kubeconfig", required=True)
    command.add_argument("--kubectl", default="kubectl")
    command.set_defaults(func=cmd_configure_argocd_local_auth)

    command = subparsers.add_parser("restore-k3s")
    command.add_argument("--proxmox-host", dest="proxmox_host", required=True)
    command.add_argument("--master-target-node", dest="proxmox_host", help=argparse.SUPPRESS)
    command.add_argument("--tofu-dir", required=True)
    command.add_argument("--backup-file", required=True)
    command.add_argument("--nas-mount-path", required=True)
    command.set_defaults(func=cmd_restore_k3s)

    command = subparsers.add_parser("shutdown-cluster")
    command.add_argument("--proxmox-host", dest="proxmox_host", required=True)
    command.add_argument("--master-target-node", dest="proxmox_host", help=argparse.SUPPRESS)
    command.add_argument("--tofu-dir", required=True)
    command.set_defaults(func=cmd_shutdown_cluster)

    command = subparsers.add_parser("remove-file")
    command.add_argument("--path", required=True)
    command.set_defaults(func=cmd_remove_file)

    command = subparsers.add_parser("clean-artifacts")
    command.set_defaults(func=cmd_clean_artifacts)

    command = subparsers.add_parser("monitor")
    command.add_argument("--master-ip", required=True)
    command.add_argument("--proxmox-host", required=True)
    command.add_argument("--kubeconfig", required=True)
    command.set_defaults(func=cmd_monitor)

    command = subparsers.add_parser("task-run")
    command.add_argument("task_args", nargs=argparse.REMAINDER)
    command.set_defaults(func=cmd_task_run)

    command = subparsers.add_parser("run-tofu")
    command.add_argument("--dir", required=True)
    command.add_argument("tofu_args", nargs=argparse.REMAINDER)
    command.set_defaults(func=cmd_run_tofu)

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
    except Exception as exc:
        print(str(exc), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
