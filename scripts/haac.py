#!/usr/bin/env python3
from __future__ import annotations

import argparse
import base64
import json
import os
import platform
import re
import shlex
import shutil
import signal
import subprocess
import sys
import tarfile
import tempfile
import time
import urllib.error
import urllib.request
import zipfile
from contextlib import contextmanager
from pathlib import Path, PurePosixPath


ROOT = Path(__file__).resolve().parent.parent
SCRIPTS_DIR = ROOT / "scripts"
K8S_DIR = ROOT / "k8s"
TOOLS_DIR = ROOT / ".tools"
TOOLS_BIN_DIR = TOOLS_DIR / "bin"
TOOLS_METADATA_PATH = TOOLS_DIR / "versions.json"
SSH_DIR = ROOT / ".ssh"
SSH_PRIVATE_KEY_PATH = SSH_DIR / "haac_ed25519"
SSH_PUBLIC_KEY_PATH = SSH_DIR / "haac_ed25519.pub"
ENV_FILE = ROOT / ".env"
PUB_CERT_PATH = SCRIPTS_DIR / "pub-sealed-secrets.pem"
SECRETS_DIR = K8S_DIR / "charts" / "haac-stack" / "templates" / "secrets"
VALUES_TEMPLATE = K8S_DIR / "charts" / "haac-stack" / "config-templates" / "values.yaml.template"
VALUES_OUTPUT = K8S_DIR / "charts" / "haac-stack" / "values.yaml"
HOOKS_DIR = ROOT / ".git" / "hooks"
KUBESEAL_VERSION = "0.36.1"
DEFAULT_WSL_DISTRO = "Debian"
TOFU_VERSION = "1.11.5"
HELM_VERSION = "4.1.3"
KUBECTL_VERSION = "1.35.3"
TASK_VERSION = "3.49.1"
SYSTEM_UPGRADE_CONTROLLER_VERSION = "v0.19.0"


class HaaCError(RuntimeError):
    pass


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
    return merged


def local_kubeconfig_path() -> Path:
    override = os.environ.get("HAAC_KUBECONFIG_PATH")
    if override:
        return Path(override)
    return Path.home() / ".kube" / "haac-k3s.yaml"


def ensure_parent(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def is_windows() -> bool:
    return os.name == "nt"


def binary_name(name: str) -> str:
    return f"{name}.exe" if is_windows() else name


def local_binary_path(name: str) -> Path:
    return TOOLS_BIN_DIR / binary_name(name)


def tool_location(name: str) -> str | None:
    local_path = local_binary_path(name)
    if local_path.exists():
        return str(local_path)
    found = shutil.which(name)
    if found:
        return found
    return None


def resolved_binary(name: str) -> str:
    return tool_location(name) or name


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


def run(
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
        stderr = completed.stderr.strip() if completed.stderr else ""
        stdout = completed.stdout.strip() if completed.stdout else ""
        detail = stderr or stdout or f"exit code {completed.returncode}"
        raise HaaCError(f"Command failed: {command_label(command)}\n{detail}")
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


def is_git_repo() -> bool:
    return (ROOT / ".git").exists()


def git_has_remote(remote_name: str = "origin") -> bool:
    if not is_git_repo():
        return False
    completed = run(["git", "remote", "get-url", remote_name], check=False, capture_output=True)
    return completed.returncode == 0


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

    env_exports = {
        key: env[key]
        for key in (
            "PROXMOX_HOST_PASSWORD",
            "LXC_PASSWORD",
            "NAS_PATH",
            "SMB_USER",
            "SMB_PASSWORD",
        )
        if key in env and env[key]
    }
    env_exports["HAAC_KUBECONFIG_PATH"] = kubeconfig_wsl

    exports = " ".join(f"{key}={shlex.quote(value)}" for key, value in env_exports.items())
    args = " ".join(shlex.quote(arg) for arg in extra_args)
    command = (
        f"cd {shlex.quote(repo_wsl)} && "
        f"mkdir -p {shlex.quote(kube_dir_wsl)} && "
        f"{exports} ansible-playbook {args} -i {shlex.quote(inventory_wsl)} {shlex.quote(playbook_wsl)}"
    ).strip()
    run(wsl_command("bash", "-lc", command, distro=wsl_distro(env)))


def rewrite_kubeconfig_server(kubeconfig: Path, server: str = "https://127.0.0.1:6443") -> None:
    if not kubeconfig.exists():
        raise HaaCError(f"Kubeconfig not found: {kubeconfig}")

    content = kubeconfig.read_text(encoding="utf-8")
    updated = re.sub(r"(^\s*server:\s*)https://.*?:6443(\s*$)", rf"\1{server}\2", content, flags=re.MULTILINE)
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


@contextmanager
def ssh_tunnel(proxmox_host: str, master_ip: str, local_port: int = 6443, remote_port: int = 6443):
    command = [
        "ssh",
        "-o",
        "StrictHostKeyChecking=no",
        "-o",
        "ExitOnForwardFailure=yes",
        "-N",
        "-L",
        f"{local_port}:{master_ip}:{remote_port}",
        f"root@{proxmox_host}",
    ]
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
            stderr = process.stderr.read().strip() if process.stderr else ""
            raise HaaCError(f"SSH tunnel failed to start: {stderr or command_label(command)}")
        yield
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


@contextmanager
def cluster_session(proxmox_host: str, master_ip: str, kubeconfig: Path, kubectl: str):
    ensure_parent(kubeconfig)
    with ssh_tunnel(proxmox_host, master_ip):
        rewrite_kubeconfig_server(kubeconfig)
        wait_for_k8s_api(kubeconfig, kubectl)
        yield


def render_env_placeholders(content: str, env: dict[str, str]) -> str:
    def replace(match: re.Match[str]) -> str:
        key = match.group(1)
        return env.get(key, match.group(0))

    return re.sub(r"\$\{([A-Z0-9_]+)\}", replace, content)


def render_values_file(env: dict[str, str]) -> None:
    content = VALUES_TEMPLATE.read_text(encoding="utf-8")
    VALUES_OUTPUT.write_text(render_env_placeholders(content, env), encoding="utf-8")


def tool_version(env: dict[str, str], env_key: str, default: str) -> str:
    return env.get(env_key, default).strip() or default


def read_tool_metadata() -> dict[str, str]:
    if not TOOLS_METADATA_PATH.exists():
        return {}
    try:
        content = json.loads(TOOLS_METADATA_PATH.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    if not isinstance(content, dict):
        return {}
    return {str(key): str(value) for key, value in content.items()}


def write_tool_metadata(metadata: dict[str, str]) -> None:
    TOOLS_DIR.mkdir(parents=True, exist_ok=True)
    TOOLS_METADATA_PATH.write_text(json.dumps(metadata, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def requested_tool_version(name: str, env: dict[str, str]) -> str:
    version_map = {
        "tofu": tool_version(env, "HAAC_TOFU_VERSION", TOFU_VERSION),
        "helm": tool_version(env, "HAAC_HELM_VERSION", HELM_VERSION),
        "kubectl": tool_version(env, "HAAC_KUBECTL_VERSION", KUBECTL_VERSION),
        "kubeseal": tool_version(env, "HAAC_KUBESEAL_VERSION", KUBESEAL_VERSION),
        "task": tool_version(env, "HAAC_TASK_VERSION", TASK_VERSION),
    }
    return version_map[name]


def install_direct_binary(url: str, destination: Path) -> str:
    TOOLS_BIN_DIR.mkdir(parents=True, exist_ok=True)
    with urllib.request.urlopen(url) as response:
        destination.write_bytes(response.read())
    if not is_windows():
        destination.chmod(0o755)
    return str(destination)


def install_zip_binary(url: str, inner_path: str, destination: Path) -> str:
    TOOLS_BIN_DIR.mkdir(parents=True, exist_ok=True)
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

    if not is_windows():
        destination.chmod(0o755)
    return str(destination)


def install_targz_binary(url: str, inner_path: str, destination: Path) -> str:
    TOOLS_BIN_DIR.mkdir(parents=True, exist_ok=True)
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

    if not is_windows():
        destination.chmod(0o755)
    return str(destination)


def ensure_local_cli_tool(name: str) -> str:
    env = merged_env()
    platform_name = host_platform()
    arch = host_arch()
    destination = local_binary_path(name)
    metadata = read_tool_metadata()
    requested_version = requested_tool_version(name, env)
    if destination.exists() and metadata.get(name) == requested_version:
        return str(destination)

    if name == "tofu":
        version = requested_version
        extension = "zip" if platform_name == "windows" else "tar.gz"
        url = f"https://github.com/opentofu/opentofu/releases/download/v{version}/tofu_{version}_{platform_name}_{arch}.{extension}"
        if platform_name == "windows":
            installed = install_zip_binary(url, "tofu.exe", destination)
        else:
            installed = install_targz_binary(url, "tofu", destination)
        metadata[name] = version
        write_tool_metadata(metadata)
        return installed

    if name == "helm":
        version = requested_version
        if platform_name == "windows":
            url = f"https://get.helm.sh/helm-v{version}-windows-{arch}.zip"
            installed = install_zip_binary(url, f"windows-{arch}/helm.exe", destination)
        else:
            url = f"https://get.helm.sh/helm-v{version}-{platform_name}-{arch}.tar.gz"
            installed = install_targz_binary(url, f"{platform_name}-{arch}/helm", destination)
        metadata[name] = version
        write_tool_metadata(metadata)
        return installed

    if name == "kubectl":
        version = requested_version
        url = f"https://dl.k8s.io/release/v{version}/bin/{platform_name}/{arch}/{binary_name('kubectl')}"
        installed = install_direct_binary(url, destination)
        metadata[name] = version
        write_tool_metadata(metadata)
        return installed

    if name == "kubeseal":
        version = requested_version
        archive_name = f"kubeseal-{version}-{platform_name}-{arch}.tar.gz"
        url = f"https://github.com/bitnami-labs/sealed-secrets/releases/download/v{version}/{archive_name}"
        installed = install_targz_binary(url, binary_name("kubeseal"), destination)
        metadata[name] = version
        write_tool_metadata(metadata)
        return installed

    if name == "task":
        version = requested_version
        if platform_name == "windows":
            url = f"https://github.com/go-task/task/releases/download/v{version}/task_windows_{arch}.zip"
            installed = install_zip_binary(url, "task.exe", destination)
        else:
            url = f"https://github.com/go-task/task/releases/download/v{version}/task_{platform_name}_{arch}.tar.gz"
            installed = install_targz_binary(url, "task", destination)
        metadata[name] = version
        write_tool_metadata(metadata)
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
    kubectl: str,
    name: str,
    namespace: str,
    *,
    literals: dict[str, str] | None = None,
    files: dict[str, Path] | None = None,
) -> str:
    command = [kubectl, "create", "secret", "generic", name, "-n", namespace]
    for key, value in (literals or {}).items():
        command.append(f"--from-literal={key}={value}")
    for key, value in (files or {}).items():
        command.append(f"--from-file={key}={value}")
    command.extend(["--dry-run=client", "-o", "yaml"])
    return run_stdout(command)


def seal_yaml(kubeseal: str, cert: Path, yaml_text: str) -> str:
    return run_stdout(
        [
            kubeseal,
            "--format=yaml",
            f"--cert={cert}",
            "--scope",
            "cluster-wide",
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
    run([kubectl, "--kubeconfig", str(kubeconfig), "apply", "-f", "-"], input_text=namespace_yaml)

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
            "--dry-run=client",
            "-o",
            "yaml",
        ]
    )
    run([kubectl, "--kubeconfig", str(kubeconfig), "apply", "-f", "-"], input_text=configmap_yaml)


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
            "HEADLAMP_OIDC_SECRET",
            "QUI_USERNAME",
            "QUI_PASSWORD",
            "QUI_OIDC_SECRET",
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
    temp_dir = Path(tempfile.mkdtemp(prefix="haac-secrets-"))
    authelia_configuration, authelia_users = render_authelia(temp_dir, env)

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
                "QUI_USERNAME": env["QUI_USERNAME"],
                "QUI_PASSWORD": env["QUI_PASSWORD"],
                "QUI_OIDC_SECRET": env["QUI_OIDC_SECRET"],
            },
            None,
        ),
        (
            "headlamp-oidc-secret",
            "mgmt",
            SECRETS_DIR / "headlamp-oidc-sealed-secret.yaml",
            {"HEADLAMP_OIDC_SECRET": env["HEADLAMP_OIDC_SECRET"]},
            None,
        ),
        (
            "argocd-sso-secret",
            "argocd",
            SECRETS_DIR / "argocd-sso-sealed-secret.yaml",
            {"clientSecret": env["ARGOCD_OIDC_SECRET"]},
            None,
        ),
        (
            "argocd-oidc-secret",
            "argocd",
            SECRETS_DIR / "argocd-oidc-sealed-secret.yaml",
            {"client_secret": env["ARGOCD_OIDC_SECRET"]},
            None,
        ),
        (
            "grafana-oidc-secret",
            "monitoring",
            SECRETS_DIR / "grafana-oidc-sealed-secret.yaml",
            {"clientSecret": env["GRAFANA_OIDC_SECRET"]},
            None,
        ),
        (
            "semaphore-db-secret",
            "mgmt",
            SECRETS_DIR / "semaphore-sealed-secret.yaml",
            {
                "POSTGRES_PASSWORD": env["SEMAPHORE_DB_PASSWORD"],
                "APP_SECRET": env["SEMAPHORE_APP_SECRET"],
                "OIDC_SECRET": env["SEMAPHORE_OIDC_SECRET"],
                "ADMIN_PASSWORD": env["SEMAPHORE_ADMIN_PASSWORD"],
            },
            None,
        ),
    ]

    ssh_key = ROOT / ".ssh" / "haac_ed25519"
    if ssh_key.exists():
        secrets.append(
            (
                "haac-ssh-key",
                "mgmt",
                SECRETS_DIR / "haac-ssh-sealed-secret.yaml",
                None,
                {"id_ed25519": ssh_key},
            )
        )

    for name, namespace, output_path, literals, files in secrets:
        secret_yaml = create_secret_yaml(kubectl, name, namespace, literals=literals, files=files)
        output_path.write_text(seal_yaml(kubeseal, cert, secret_yaml), encoding="utf-8")

    render_values_file(env)


def apply_rendered_file(file_path: Path, kubeconfig: Path, kubectl: str, env: dict[str, str]) -> None:
    content = render_env_placeholders(file_path.read_text(encoding="utf-8"), env)
    run([kubectl, "--kubeconfig", str(kubeconfig), "apply", "-f", "-"], input_text=content)


def wait_for_jsonpath(
    kubectl: str,
    kubeconfig: Path,
    command: list[str],
    *,
    expected: str,
    timeout_seconds: int,
    interval_seconds: int = 10,
    degraded_check: list[str] | None = None,
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
                raise HaaCError("haac-stack is degraded according to ArgoCD")
        time.sleep(interval_seconds)
    raise HaaCError(f"Timeout waiting for {' '.join(command)} (last value: {last_value})")


def sync_repo() -> None:
    if not is_git_repo():
        print("Skipping git sync: repository metadata not found.")
        return
    env = merged_env()
    revision = gitops_revision(env)

    run(["git", "add", "."])
    run(["git", "commit", "-m", "Auto-save before sync [skip ci]", "--no-verify"], check=False)

    if not git_has_remote("origin"):
        print("Skipping remote sync: git remote 'origin' not configured.")
        return

    remote_ref = f"origin/{revision}"
    run(["git", "fetch", "origin", revision], check=False)
    run(["git", "merge", remote_ref, "-X", "ours", "--no-edit"], check=False)


def push_changes(push_all: bool, kubectl: str, kubeconfig: Path) -> None:
    if not is_git_repo():
        print("Skipping git push: repository metadata not found.")
        return
    env = merged_env()
    revision = gitops_revision(env)

    run(["git", "add", "."])
    run(["git", "commit", "-m", "Auto-commit manual work [skip ci]", "--no-verify"], check=False)

    if git_has_remote("origin"):
        remote_ref = f"origin/{revision}"
        run(["git", "fetch", "origin", revision], check=False)
        run(["git", "merge", remote_ref, "-X", "ours", "--no-edit"], check=False)

    generate_secrets_core(kubeconfig, kubectl, fetch_cert=False)

    if push_all:
        run(["git", "add", "."])
    else:
        run(["git", "add", str(SECRETS_DIR), str(VALUES_OUTPUT)])

    staged = run(["git", "diff", "--cached", "--quiet"], check=False)
    if staged.returncode == 0:
        print("No new changes to push.")
        return

    amended = run(["git", "commit", "--amend", "--no-edit", "--no-verify"], check=False)
    if amended.returncode != 0:
        run(["git", "commit", "-m", "Updated infrastructure [skip ci]", "--no-verify"], check=False)

    if git_has_remote("origin"):
        run(["git", "push", "origin", revision], check=False)


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
            if is_git_repo():
                run(["git", "add", str(SECRETS_DIR), str(VALUES_OUTPUT)], check=False)
            return

    print("K3s is not reachable from the pre-commit hook. Skipping secret regeneration.")


def deploy_argocd(master_ip: str, proxmox_host: str, kubeconfig: Path, kubectl: str) -> None:
    env = merged_env()
    with cluster_session(proxmox_host, master_ip, kubeconfig, kubectl):
        root_app = render_env_placeholders((K8S_DIR / "argocd-apps.yaml").read_text(encoding="utf-8"), env)
        run([kubectl, "--kubeconfig", str(kubeconfig), "apply", "-f", "-"], input_text=root_app)


def deploy_local(master_ip: str, proxmox_host: str, kubeconfig: Path, kubectl: str, helm: str) -> None:
    env = merged_env()
    with cluster_session(proxmox_host, master_ip, kubeconfig, kubectl):
        apply_rendered_file(K8S_DIR / "bootstrap" / "root" / "namespaces.yaml", kubeconfig, kubectl, env)
        run(
            [
                kubectl,
                "--kubeconfig",
                str(kubeconfig),
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
                str(kubeconfig),
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
                str(kubeconfig),
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
                str(kubeconfig),
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
    with cluster_session(proxmox_host, master_ip, kubeconfig, kubectl):
        if run([kubectl, "--kubeconfig", str(kubeconfig), "get", "applications", "-n", "argocd"], check=False).returncode != 0:
            raise HaaCError("ArgoCD API server is not reachable")

        wait_for_jsonpath(
            kubectl,
            kubeconfig,
            ["get", "application", "haac-stack", "-n", "argocd", "-o", "jsonpath={.status.sync.status}"],
            expected="Synced",
            timeout_seconds=timeout_seconds,
            degraded_check=["get", "application", "haac-stack", "-n", "argocd", "-o", "jsonpath={.status.health.status}"],
        )

        deadline = time.time() + timeout_seconds
        while time.time() < deadline:
            if run([kubectl, "--kubeconfig", str(kubeconfig), "get", "secret", "protonvpn-key", "-n", "media"], check=False).returncode == 0:
                break
            time.sleep(10)
        else:
            raise HaaCError("Timed out waiting for secret media/protonvpn-key")

        while time.time() < deadline:
            ready = run_stdout(
                [
                    kubectl,
                    "--kubeconfig",
                    str(kubeconfig),
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
                        str(kubeconfig),
                        "get",
                        "job",
                        "downloaders-bootstrap",
                        "-n",
                        "media",
                    ],
                    check=False,
                )
                if bootstrap_job.returncode == 0:
                    run(
                        [
                            kubectl,
                            "--kubeconfig",
                            str(kubeconfig),
                            "wait",
                            "--for=condition=complete",
                            "job/downloaders-bootstrap",
                            "-n",
                            "media",
                            "--timeout=300s",
                        ],
                        check=False,
                    )
                return
            time.sleep(10)
        raise HaaCError("Timed out waiting for downloaders pod readiness")


def verify_cluster(master_ip: str, proxmox_host: str, kubeconfig: Path, kubectl: str) -> None:
    with cluster_session(proxmox_host, master_ip, kubeconfig, kubectl):
        sections = [
            (["get", "nodes", "-o", "wide"], "--- Node Status ---"),
            (["get", "pods", "-A"], "--- Pod Health ---"),
            (["get", "nodes", "-o", 'custom-columns=NAME:.metadata.name,GPU_ALLOCATABLE:.status.allocatable.nvidia\\.com/gpu'], "--- GPU Allocation ---"),
            (["get", "pods", "-n", "kube-system", "-l", "name=nvidia-device-plugin-ds"], "--- NVIDIA Device Plugin Pods ---"),
            (["get", "pvc", "-A"], "--- PVCs ---"),
            (["get", "pv"], "--- PVs ---"),
            (["get", "ingress", "-A"], "--- Ingress ---"),
            (["get", "certificates", "-A"], "--- Certificates ---"),
        ]
        for command, title in sections:
            print(title)
            completed = run([kubectl, "--kubeconfig", str(kubeconfig), *command], check=False, capture_output=True)
            print((completed.stdout or completed.stderr).strip())
            print()


def verify_web(domain_name: str, retries: int = 30, sleep_seconds: int = 10) -> None:
    urls = [
        f"https://home.{domain_name}",
        f"https://jellyfin.{domain_name}",
        f"https://argocd.{domain_name}",
        f"https://longhorn.{domain_name}",
        f"https://sonarr.{domain_name}",
        f"https://radarr.{domain_name}",
        f"https://prowlarr.{domain_name}",
        f"https://qui.{domain_name}",
        f"https://autobrr.{domain_name}",
        f"https://headlamp.{domain_name}",
    ]
    accepted_statuses = {200, 201, 202, 204, 301, 302, 307, 308, 401}

    for url in urls:
        success = False
        for _ in range(retries):
            request = urllib.request.Request(url, method="GET")
            try:
                with urllib.request.urlopen(request, timeout=10) as response:
                    status = response.status
            except urllib.error.HTTPError as error:
                status = error.code
            except Exception:
                status = 0
            if status in accepted_statuses:
                success = True
                break
            time.sleep(sleep_seconds)
        if not success:
            raise HaaCError(f"Endpoint not reachable after retries: {url}")


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

    ingress = current_config["result"]["config"].get("ingress", [])
    domain_name = env["DOMAIN_NAME"]
    filtered = [
        item
        for item in ingress
        if item.get("service") != "http_status:404"
        and item.get("hostname") not in {f"*.{domain_name}", domain_name}
    ]
    filtered.extend(
        [
            {
                "hostname": f"*.{domain_name}",
                "service": "http://traefik.kube-system.svc.cluster.local:80",
                "originRequest": {"noTLSVerify": True},
            },
            {
                "hostname": domain_name,
                "service": "http://traefik.kube-system.svc.cluster.local:80",
                "originRequest": {"noTLSVerify": True},
            },
            {"service": "http_status:404"},
        ]
    )
    update_payload = {"config": {**current_config["result"]["config"], "ingress": filtered}}
    updated = cloudflare_request("PUT", config_url, env["CLOUDFLARE_API_TOKEN"], update_payload)
    if not updated.get("success"):
        raise HaaCError(f"Failed to update Cloudflare tunnel configuration: {updated}")

    dns_url = f"https://api.cloudflare.com/client/v4/zones/{env['CLOUDFLARE_ZONE_ID']}/dns_records?per_page=100"
    all_records = cloudflare_request("GET", dns_url, env["CLOUDFLARE_API_TOKEN"])
    if not all_records.get("success"):
        raise HaaCError(f"Failed to retrieve Cloudflare DNS records: {all_records}")

    expected_target = f"{tunnel_id}.cfargotunnel.com"
    for record_name in (f"*.{domain_name}", domain_name):
        existing = [item for item in all_records.get("result", []) if item.get("name") == record_name]
        valid = False
        for record in existing:
            if record.get("type") == "CNAME" and record.get("content") == expected_target:
                valid = True
                continue
            delete_url = f"https://api.cloudflare.com/client/v4/zones/{env['CLOUDFLARE_ZONE_ID']}/dns_records/{record['id']}"
            deleted = cloudflare_request("DELETE", delete_url, env["CLOUDFLARE_API_TOKEN"])
            if not deleted.get("success"):
                raise HaaCError(f"Failed to delete conflicting DNS record: {deleted}")

        if not valid:
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
    with cluster_session(proxmox_host, master_ip, kubeconfig, kubectl):
        argocd_pod = get_pod_name(kubectl, kubeconfig, "argocd", "app.kubernetes.io/name=argocd-server")
        if not argocd_pod:
            raise HaaCError("ArgoCD server pod not found while configuring local auth")

        bcrypt_hash = run_stdout(
            [
                kubectl,
                "--kubeconfig",
                str(kubeconfig),
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
                    str(kubeconfig),
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
                str(kubeconfig),
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
                str(kubeconfig),
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
                str(kubeconfig),
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
    require_env(["QUI_USERNAME", "QUI_PASSWORD"], env)
    qui_user = env["QUI_USERNAME"]
    qui_password = env["QUI_PASSWORD"]

    with cluster_session(proxmox_host, master_ip, kubeconfig, kubectl):
        deadline = time.time() + 600
        pod_name = ""
        while time.time() < deadline:
            pod_name = run_stdout(
                [
                    kubectl,
                    "--kubeconfig",
                    str(kubeconfig),
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
                        str(kubeconfig),
                        "exec",
                        "-n",
                        "media",
                        pod_name,
                        "-c",
                        "qui",
                        "--",
                        "wget",
                        "--spider",
                        "-S",
                        "http://localhost:7476/api/auth/validate",
                    ],
                    check=False,
                    capture_output=True,
                )
                if "HTTP/" in (health.stderr or health.stdout or ""):
                    break
            time.sleep(5)
        else:
            raise HaaCError("QUI API did not become available before timeout")

        run(
            [
                kubectl,
                "--kubeconfig",
                str(kubeconfig),
                "exec",
                "-n",
                "media",
                pod_name,
                "-c",
                "qui",
                "--",
                "wget",
                "-qO-",
                '--post-data={"username":"%s","password":"%s"}' % (qui_user, qui_password),
                "--header=Content-Type: application/json",
                "http://localhost:7476/api/auth/setup",
            ],
            check=False,
        )

        logs = run(
            [
                kubectl,
                "--kubeconfig",
                str(kubeconfig),
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

        if temp_password:
            run(
                [
                    kubectl,
                    "--kubeconfig",
                    str(kubeconfig),
                    "exec",
                    "-n",
                    "media",
                    pod_name,
                    "-c",
                    "qui",
                    "--",
                    "wget",
                    "-qO-",
                    f"--post-data=username=admin&password={temp_password}",
                    "--header=Content-Type: application/x-www-form-urlencoded",
                    "--save-cookies",
                    "/tmp/qbit_cookies.txt",
                    "--keep-session-cookies",
                    "http://localhost:8080/api/v2/auth/login",
                ],
                check=False,
            )
            run(
                [
                    kubectl,
                    "--kubeconfig",
                    str(kubeconfig),
                    "exec",
                    "-n",
                    "media",
                    pod_name,
                    "-c",
                    "qui",
                    "--",
                    "wget",
                    "-qO-",
                    f"--post-data=new_password={qui_password}",
                    "--header=Content-Type: application/x-www-form-urlencoded",
                    "--load-cookies",
                    "/tmp/qbit_cookies.txt",
                    "http://localhost:8080/api/v2/auth/changePassword",
                ],
                check=False,
            )

        run(
            [
                kubectl,
                "--kubeconfig",
                str(kubeconfig),
                "exec",
                "-n",
                "media",
                pod_name,
                "-c",
                "qui",
                "--",
                "wget",
                "-qO-",
                '--post-data={"username":"%s","password":"%s"}' % (qui_user, qui_password),
                "--header=Content-Type: application/json",
                "--save-cookies",
                "/tmp/cookies.txt",
                "--keep-session-cookies",
                "http://localhost:7476/api/auth/login",
            ],
            check=False,
        )
        run(
            [
                kubectl,
                "--kubeconfig",
                str(kubeconfig),
                "exec",
                "-n",
                "media",
                pod_name,
                "-c",
                "qui",
                "--",
                "wget",
                "-qO-",
                '--post-data={"name":"qBittorrent","type":"qbittorrent","enabled":true,"host":"localhost","port":8080,"tls":false,"tls_skip_verify":true,"username":"admin","password":"%s","settings":{"basic_auth":false}}'
                % qui_password,
                "--header=Content-Type: application/json",
                "--load-cookies",
                "/tmp/cookies.txt",
                "http://localhost:7476/api/download_clients",
            ],
            check=False,
        )


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


def shutdown_cluster(master_target_node: str, tofu_dir: Path) -> None:
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
        status = run(
            ["ssh", "-o", "StrictHostKeyChecking=no", f"root@{master_target_node}", f"pct status {vmid}"],
            check=False,
            capture_output=True,
        )
        if "status: running" not in (status.stdout or ""):
            continue
        run(
            [
                "ssh",
                "-o",
                "StrictHostKeyChecking=no",
                f"root@{master_target_node}",
                f"pct exec {vmid} -- bash -lc 'systemctl stop k3s 2>/dev/null || true; systemctl stop k3s-agent 2>/dev/null || true'",
            ],
            check=False,
        )
        graceful = run(
            [
                "ssh",
                "-o",
                "StrictHostKeyChecking=no",
                f"root@{master_target_node}",
                f"pct shutdown {vmid} --timeout 180",
            ],
            check=False,
        )
        if graceful.returncode != 0:
            run(["ssh", "-o", "StrictHostKeyChecking=no", f"root@{master_target_node}", f"pct stop {vmid}"], check=False)
        print(f"Shutdown requested for {label} ({vmid})")


def restore_k3s(master_target_node: str, tofu_dir: Path, backup_file: str, nas_mount_path: str) -> None:
    master_vmid = run_stdout([resolved_binary("tofu"), f"-chdir={tofu_dir}", "output", "-raw", "master_vmid"])
    run(
        [
            "ssh",
            "-o",
            "StrictHostKeyChecking=no",
            f"root@{master_target_node}",
            f"pct exec {master_vmid} -- systemctl stop k3s",
        ]
    )

    restore_script = f"""
set -e
LXC_ID={shlex.quote(master_vmid)}
pct exec "$LXC_ID" -- mv /var/lib/rancher/k3s/server/db/state.db /var/lib/rancher/k3s/server/db/state.db.corrupted-$(date +%s) || true
cp {shlex.quote(nas_mount_path)}/{shlex.quote(backup_file)} /var/lib/lxc/$LXC_ID/rootfs/var/lib/rancher/k3s/server/db/state.db
pct exec "$LXC_ID" -- chown root:root /var/lib/rancher/k3s/server/db/state.db
"""
    run(["ssh", "-o", "StrictHostKeyChecking=no", f"root@{master_target_node}", "bash", "-lc", restore_script])
    run(
        [
            "ssh",
            "-o",
            "StrictHostKeyChecking=no",
            f"root@{master_target_node}",
            f"pct exec {master_vmid} -- systemctl start k3s",
        ]
    )


def remove_file(path: Path) -> None:
    if path.exists():
        path.unlink()


def monitor(master_ip: str, proxmox_host: str, kubeconfig: Path) -> None:
    k9s = shutil.which("k9s")
    if not k9s:
        raise HaaCError("k9s is not installed or not on PATH.")
    with cluster_session(proxmox_host, master_ip, kubeconfig, resolved_binary("kubectl")):
        subprocess.run([k9s, "--all-namespaces"], cwd=str(ROOT), check=False)


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


def doctor() -> None:
    env = merged_env()
    failures: list[str] = []
    checks = [
        ("python", "python"),
        ("git", "git"),
        ("ssh", "ssh"),
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
            for label, command in (
                ("ansible-playbook", "command -v ansible-playbook"),
                ("git", "command -v git"),
                ("python3", "command -v python3"),
                ("ssh", "command -v ssh"),
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


def install_wsl_tools() -> None:
    if not is_windows():
        raise HaaCError("install-wsl-tools is supported only on Windows.")
    if shutil.which("wsl") is None:
        raise HaaCError("WSL is not installed. Install WSL and Debian first, then rerun this command.")

    env = merged_env()
    distro = wsl_distro(env)
    distro_check = run(["wsl", "-l", "-q"], check=False, capture_output=True)
    available_distros = {
        line.strip().replace("\x00", "")
        for line in (distro_check.stdout or "").splitlines()
        if line.strip()
    }
    if distro not in available_distros:
        raise HaaCError(f"WSL distro '{distro}' was not found. Install it first, then rerun this command.")

    print(f"Installing WSL packages in {distro}...")
    run(
        wsl_command(
            "bash",
            "-lc",
            "apt-get update && DEBIAN_FRONTEND=noninteractive apt-get install -y ansible git python3 openssh-client",
            distro=distro,
            user="root",
        )
    )


def install_tools() -> None:
    for binary in ("tofu", "helm", "kubectl", "kubeseal", "task"):
        installed = ensure_local_cli_tool(binary)
        print(f"Installed portable {binary} at {installed}")

    missing_global = [binary for binary in ("python", "git", "ssh") if tool_location(binary) is None]
    if missing_global:
        raise HaaCError(
            "Missing required global tooling that is not bootstrapped locally: " + ", ".join(missing_global)
        )

    ensure_repo_ssh_keypair()

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
            "GITOPS_REPO_URL",
            "GITOPS_REPO_REVISION",
        ],
        env,
    )


def cmd_kubeconfig_path(_: argparse.Namespace) -> None:
    print(local_kubeconfig_path())


def cmd_tool_path(args: argparse.Namespace) -> None:
    if args.name in bootstrappable_tools():
        print(ensure_local_cli_tool(args.name))
        return
    print(resolved_binary(args.name))


def cmd_doctor(_: argparse.Namespace) -> None:
    doctor()


def cmd_install_windows_tools(_: argparse.Namespace) -> None:
    install_tools()


def cmd_install_tools(_: argparse.Namespace) -> None:
    install_tools()


def cmd_install_wsl_tools(_: argparse.Namespace) -> None:
    install_wsl_tools()


def resolve_default_gateway(env: dict[str, str]) -> str:
    if env.get("LXC_GATEWAY"):
        return env["LXC_GATEWAY"]
    host = env.get("MASTER_TARGET_NODE", "pve")
    completed = run(
        [
            "ssh",
            "-o",
            "StrictHostKeyChecking=no",
            f"root@{host}",
            "ip route | awk '/default/ {print $3; exit}'",
        ],
        check=False,
        capture_output=True,
    )
    if completed.returncode == 0:
        return completed.stdout.strip()
    return ""


def tofu_cli_env() -> dict[str, str]:
    env = merged_env()
    mapped = os.environ.copy()
    mapped.update(
        {
            "TF_VAR_lxc_password": env.get("LXC_PASSWORD", ""),
            "TF_VAR_lxc_rootfs_datastore": env.get("LXC_ROOTFS_DATASTORE", ""),
            "TF_VAR_lxc_master_hostname": env.get("LXC_MASTER_HOSTNAME", ""),
            "TF_VAR_lxc_unprivileged": env.get("LXC_UNPRIVILEGED", ""),
            "TF_VAR_lxc_nesting": env.get("LXC_NESTING", ""),
            "TF_VAR_master_target_node": env.get("MASTER_TARGET_NODE", ""),
            "TF_VAR_k3s_master_ip": env.get("K3S_MASTER_IP", ""),
            "TF_VAR_lxc_gateway": resolve_default_gateway(env),
            "TF_VAR_worker_nodes": env.get("WORKER_NODES_JSON", ""),
            "TF_VAR_host_nas_path": env.get("HOST_NAS_PATH", ""),
            "TF_VAR_cloudflare_tunnel_token": env.get("CLOUDFLARE_TUNNEL_TOKEN", ""),
            "TF_VAR_domain_name": env.get("DOMAIN_NAME", ""),
            "TF_VAR_protonvpn_openvpn_username": env.get("PROTONVPN_OPENVPN_USERNAME", ""),
            "TF_VAR_protonvpn_openvpn_password": env.get("PROTONVPN_OPENVPN_PASSWORD", ""),
            "TF_VAR_smb_user": env.get("SMB_USER", ""),
            "TF_VAR_smb_password": env.get("SMB_PASSWORD", ""),
            "TF_VAR_nas_address": env.get("NAS_ADDRESS", ""),
            "TF_VAR_nas_share_name": env.get("NAS_SHARE_NAME", ""),
            "TF_VAR_storage_uid": env.get("STORAGE_UID", ""),
            "TF_VAR_storage_gid": env.get("STORAGE_GID", ""),
            "TF_VAR_python_executable": env.get("PYTHON_CMD", "python"),
        }
    )
    return mapped


def run_tofu_command(tofu_dir: Path, arguments: list[str]) -> None:
    tofu_binary = resolved_binary("tofu")
    run([tofu_binary, f"-chdir={tofu_dir}", *arguments], env=tofu_cli_env())


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


def cmd_sync_repo(_: argparse.Namespace) -> None:
    sync_repo()


def cmd_setup_hooks(_: argparse.Namespace) -> None:
    install_hooks()


def cmd_pre_commit_hook(_: argparse.Namespace) -> None:
    pre_commit_hook()


def cmd_run_ansible(args: argparse.Namespace) -> None:
    env = merged_env()
    inventory = ROOT / args.inventory
    playbook = ROOT / args.playbook
    extra_args = shlex.split(args.extra_args) if args.extra_args else []
    if is_windows():
        run_ansible_wsl(inventory, playbook, extra_args, env)
        return

    env["HAAC_KUBECONFIG_PATH"] = str(local_kubeconfig_path())
    ensure_parent(local_kubeconfig_path())
    run(["ansible-playbook", *extra_args, "-i", str(inventory), str(playbook)], env=env)


def cmd_generate_secrets(args: argparse.Namespace) -> None:
    kubeconfig = Path(args.kubeconfig)
    with cluster_session(args.proxmox_host, args.master_ip, kubeconfig, args.kubectl):
        generate_secrets_core(kubeconfig, args.kubectl, fetch_cert=True)
        upload_inventory_configmap(args.kubectl, kubeconfig)


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


def cmd_verify_web(args: argparse.Namespace) -> None:
    verify_web(args.domain)


def cmd_sync_cloudflare(_: argparse.Namespace) -> None:
    sync_cloudflare()


def cmd_configure_apps(args: argparse.Namespace) -> None:
    bootstrap_downloaders(args.master_ip, args.proxmox_host, Path(args.kubeconfig), args.kubectl)


def cmd_configure_argocd_local_auth(args: argparse.Namespace) -> None:
    configure_argocd_local_auth(args.master_ip, args.proxmox_host, Path(args.kubeconfig), args.kubectl)


def cmd_restore_k3s(args: argparse.Namespace) -> None:
    restore_k3s(args.master_target_node, Path(args.tofu_dir), args.backup_file, args.nas_mount_path)


def cmd_shutdown_cluster(args: argparse.Namespace) -> None:
    shutdown_cluster(args.master_target_node, Path(args.tofu_dir))


def cmd_remove_file(args: argparse.Namespace) -> None:
    remove_file(Path(args.path))


def cmd_monitor(args: argparse.Namespace) -> None:
    monitor(args.master_ip, args.proxmox_host, Path(args.kubeconfig))


def cmd_task_run(args: argparse.Namespace) -> None:
    task_args = list(args.task_args)
    if task_args and task_args[0] == "--":
        task_args = task_args[1:]
    if not task_args:
        raise HaaCError("Please pass the task arguments after `--`, for example: task-run -- up")
    task_binary = ensure_local_cli_tool("task")
    completed = subprocess.run([task_binary, *task_args], cwd=str(ROOT), check=False)
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

    command = subparsers.add_parser("verify-web")
    command.add_argument("--domain", required=True)
    command.set_defaults(func=cmd_verify_web)

    command = subparsers.add_parser("sync-cloudflare")
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
    command.add_argument("--master-target-node", required=True)
    command.add_argument("--tofu-dir", required=True)
    command.add_argument("--backup-file", required=True)
    command.add_argument("--nas-mount-path", required=True)
    command.set_defaults(func=cmd_restore_k3s)

    command = subparsers.add_parser("shutdown-cluster")
    command.add_argument("--master-target-node", required=True)
    command.add_argument("--tofu-dir", required=True)
    command.set_defaults(func=cmd_shutdown_cluster)

    command = subparsers.add_parser("remove-file")
    command.add_argument("--path", required=True)
    command.set_defaults(func=cmd_remove_file)

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
