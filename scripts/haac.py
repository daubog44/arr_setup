#!/usr/bin/env python3
from __future__ import annotations

import argparse
import base64
import configparser
import copy
import hashlib
import http.client
import http.cookiejar
import ipaddress
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
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid
import xml.etree.ElementTree as ET
import zipfile
from contextlib import contextmanager
from pathlib import Path, PurePosixPath

from haaclib import endpoints as endpointlib
from haaclib import envdefaults as envdefaultslib
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
TRAEFIK_CONFIG_OUTPUT = K8S_DIR / "platform" / "traefik" / "traefik-config.yaml"
CROWDSEC_APP_OUTPUT = K8S_DIR / "platform" / "applications" / "crowdsec-app.yaml"
CROWDSEC_LAPI_SECRET_OUTPUT = K8S_DIR / "platform" / "crowdsec" / "crowdsec-lapi-sealed-secret.yaml"
CROWDSEC_TRAEFIK_SECRET_OUTPUT = K8S_DIR / "platform" / "traefik" / "crowdsec-bouncer-sealed-secret.yaml"
LITMUS_ADMIN_SECRET_OUTPUT = K8S_DIR / "platform" / "chaos" / "litmus-admin-credentials-sealed-secret.yaml"
LITMUS_MONGODB_SECRET_OUTPUT = K8S_DIR / "platform" / "chaos" / "litmus-mongodb-credentials-sealed-secret.yaml"
LITMUS_MONGODB_SECRET_NAME = "litmus-mongodb-credentials"
LITMUS_CHAOS_CATALOG_INDEX = K8S_DIR / "platform" / "chaos" / "litmus-workflow-catalog" / "catalog.json"
HOMEPAGE_WIDGETS_SECRET_OUTPUT = SECRETS_DIR / "homepage-widgets-sealed-secret.yaml"
SEMAPHORE_MAINTENANCE_SSH_SECRET_OUTPUT = SECRETS_DIR / "semaphore-maintenance-ssh-sealed-secret.yaml"
SEMAPHORE_REPO_DEPLOY_SSH_SECRET_OUTPUT = SECRETS_DIR / "semaphore-repo-deploy-ssh-sealed-secret.yaml"
RECYCLARR_CONFIG_TEMPLATE = (
    K8S_DIR / "charts" / "haac-stack" / "charts" / "media" / "files" / "recyclarr" / "recyclarr.yml"
)
RECYCLARR_CONFIG_MAP_NAME = "recyclarr-config"
RECYCLARR_SECRET_NAME = "recyclarr-secrets"
TRAEFIK_DEFAULT_TRUSTED_IPS = (
    "10.42.0.0/16,10.43.0.0/16,103.21.244.0/22,103.22.200.0/22,103.31.4.0/22,"
    "104.16.0.0/13,104.24.0.0/14,108.162.192.0/18,131.0.72.0/22,141.101.64.0/18,"
    "162.158.0.0/15,172.64.0.0/13,173.245.48.0/20,188.114.96.0/20,190.93.240.0/20,"
    "197.234.240.0/22,198.41.128.0/17,2400:cb00::/32,2606:4700::/32,2803:f800::/32,"
    "2405:b500::/32,2405:8100::/32,2a06:98c0::/29,2c0f:f248::/32"
)
GITOPS_RENDERED_OUTPUTS = (
    K8S_DIR / "argocd-apps.yaml",
    K8S_DIR / "bootstrap" / "root" / "applications" / "platform-root.yaml",
    K8S_DIR / "bootstrap" / "root" / "applications" / "workloads-root.yaml",
    K8S_DIR / "workloads" / "applications" / "haac-stack.yaml",
    K8S_DIR / "platform" / "argocd" / "argocd-app.yaml",
    K8S_DIR / "platform" / "argocd" / "install-overlay" / "argocd-cm.yaml",
    K8S_DIR / "platform" / "applications" / "falco-app.yaml",
    K8S_DIR / "platform" / "falco-ingest-service.yaml",
    TRAEFIK_CONFIG_OUTPUT,
    CROWDSEC_APP_OUTPUT,
    K8S_DIR / "platform" / "applications" / "kyverno-app.yaml",
    K8S_DIR / "platform" / "applications" / "kyverno-policies-app.yaml",
    K8S_DIR / "platform" / "applications" / "kube-prometheus-stack-app.yaml",
    K8S_DIR / "platform" / "applications" / "policy-reporter-app.yaml",
    K8S_DIR / "platform" / "applications" / "semaphore-app.yaml",
)
GITOPS_GENERATED_OUTPUTS = (
    VALUES_OUTPUT,
    ARGOCD_OIDC_SECRET_OUTPUT,
    CROWDSEC_LAPI_SECRET_OUTPUT,
    CROWDSEC_TRAEFIK_SECRET_OUTPUT,
    LITMUS_ADMIN_SECRET_OUTPUT,
    LITMUS_MONGODB_SECRET_OUTPUT,
    *GITOPS_RENDERED_OUTPUTS,
)
FALCO_APP_OUTPUT = K8S_DIR / "platform" / "applications" / "falco-app.yaml"
FALCO_INGEST_SERVICE_OUTPUT = K8S_DIR / "platform" / "falco-ingest-service.yaml"
DISABLED_GITOPS_LIST = "apiVersion: v1\nkind: List\nitems: []\n"
SECURITY_SIGNAL_RESIDUE_TARGETS = {
    "argocd": ("argocd-repo-server-", "argocd-redis-"),
    "security": ("falco-falcosidekick-ui-", "trivy-operator-"),
}
TRIVY_NAMESPACED_REPORT_RESOURCES = (
    "configauditreports.aquasecurity.github.io",
    "exposedsecretreports.aquasecurity.github.io",
    "rbacassessmentreports.aquasecurity.github.io",
    "vulnerabilityreports.aquasecurity.github.io",
)
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
    ROOT / ".playwright",
    ROOT / ".playwright-cli",
)
LEGACY_ARTIFACT_PATTERNS = (
    ".tmp-*.log",
    "haac-*.log",
    "loop-*.log",
    "master-*.log",
    "worker*-*.log",
)
SANCTIONED_SCRATCH_ROOTS = (
    TMP_DIR,
)


class HaaCError(RuntimeError):
    pass


UP_TASK_LINE_PATTERN = re.compile(r"^task: \[([^\]]+)\]\s+(.*)$")
UP_RECOVERY_FAILING_PATTERN = re.compile(r"^\[recovery\] Failing phase: (.+)$")
UP_RECOVERY_LAST_VERIFIED_PATTERN = re.compile(r"^\[recovery\] Last verified phase: (.+)$")
UP_RECOVERY_RERUN_PATTERN = re.compile(r"^\[recovery\] Full rerun guidance: (.+)$")
UP_TASK_PHASES = {
    "preflight": "Preflight",
    "check-env": "Preflight",
    "doctor": "Preflight",
    "sync": "Preflight",
    "setup-hooks": "Preflight",
    "provision-infra": "Infrastructure provisioning",
    "configure-os": "Node configuration",
    "gitops-bootstrap": "GitOps publication",
    "internal:gitops-bootstrap": "GitOps publication",
    "generate-secrets": "GitOps publication",
    "internal:generate-secrets": "GitOps publication",
    "push-changes": "GitOps publication",
    "internal:push-changes": "GitOps publication",
    "deploy-argocd": "GitOps publication",
    "internal:deploy-argocd": "GitOps publication",
    "wait-for-argocd-sync": "GitOps readiness",
    "internal:wait-for-argocd-sync": "GitOps readiness",
    "security:post-install": "GitOps readiness",
    "chaos:post-install": "GitOps readiness",
    "media:post-install": "GitOps readiness",
    "internal:repair-litmus-admin": "GitOps readiness",
    "internal:repair-litmus-chaos": "GitOps readiness",
    "sync-cloudflare": "Cloudflare publication",
    "internal:sync-cloudflare": "Cloudflare publication",
    "verify-all": "Cluster verification",
    "verify-cluster": "Cluster verification",
    "internal:verify-cluster": "Cluster verification",
    "verify-endpoints": "Public URL verification",
    "internal:verify-endpoints": "Public URL verification",
    "internal:verify-browser-auth": "Public URL verification",
}
ARR_PING_SUCCESS_PATTERN = r'"status"\s*:\s*"OK"|pong'
SEERR_JELLYFIN_INTERNAL_HOST = "jellyfin.media.svc.cluster.local"
SEERR_JELLYFIN_INTERNAL_PORT = 80
SEERR_JELLYFIN_SERVER_TYPE = 2
QBITTORRENT_INTERNAL_HOST = "qbittorrent.media.svc.cluster.local"
QBITTORRENT_INTERNAL_PORT = 8080
QBITTORRENT_SHARED_DOWNLOAD_PATH = "/data/torrents"
QBITTORRENT_SHARED_INCOMPLETE_PATH = "/data/torrents/incomplete"
BAZARR_INTERNAL_URL = "http://bazarr.media.svc.cluster.local"
PROWLARR_INTERNAL_URL = "http://prowlarr.media.svc.cluster.local"
RADARR_INTERNAL_URL = "http://radarr.media.svc.cluster.local"
SONARR_INTERNAL_URL = "http://sonarr.media.svc.cluster.local"
LIDARR_INTERNAL_URL = "http://lidarr.media.svc.cluster.local"
WHISPARR_INTERNAL_URL = "http://whisparr.media.svc.cluster.local"
SABNZBD_INTERNAL_URL = "http://sabnzbd.media.svc.cluster.local"
SABNZBD_INTERNAL_HOST = "sabnzbd.media.svc.cluster.local"
SABNZBD_INTERNAL_PORT = 80
SABNZBD_COMPLETE_DOWNLOAD_PATH = "/data/usenet/complete"
SABNZBD_INCOMPLETE_DOWNLOAD_PATH = "/data/usenet/incomplete"
BAZARR_DEFAULT_LANGUAGE_CODES = ("it", "en")
BAZARR_DEFAULT_PROFILE_ID = 1
ARR_QBITTORRENT_CLIENT_NAME = "qBittorrent"
ARR_SABNZBD_CLIENT_NAME = "SABnzbd"
ARR_QBITTORRENT_CATEGORIES = {
    "radarr": "radarr",
    "sonarr": "tv-sonarr",
    "lidarr": "lidarr",
    "whisparr": "whisparr",
    "prowlarr": "prowlarr",
}
ARR_QBITTORRENT_IMPORTED_CATEGORIES = {
    "radarr": "radarr-imported",
    "sonarr": "tv-sonarr-imported",
    "lidarr": "lidarr-imported",
    "whisparr": "whisparr-imported",
}
ARR_QBITTORRENT_CATEGORY_SAVE_PATHS = {
    ARR_QBITTORRENT_CATEGORIES["radarr"]: f"{QBITTORRENT_SHARED_DOWNLOAD_PATH}/radarr",
    ARR_QBITTORRENT_CATEGORIES["sonarr"]: f"{QBITTORRENT_SHARED_DOWNLOAD_PATH}/tv-sonarr",
    ARR_QBITTORRENT_CATEGORIES["lidarr"]: f"{QBITTORRENT_SHARED_DOWNLOAD_PATH}/lidarr",
    ARR_QBITTORRENT_CATEGORIES["whisparr"]: f"{QBITTORRENT_SHARED_DOWNLOAD_PATH}/whisparr",
    ARR_QBITTORRENT_CATEGORIES["prowlarr"]: f"{QBITTORRENT_SHARED_DOWNLOAD_PATH}/prowlarr",
    ARR_QBITTORRENT_IMPORTED_CATEGORIES["radarr"]: f"{QBITTORRENT_SHARED_DOWNLOAD_PATH}/radarr-imported",
    ARR_QBITTORRENT_IMPORTED_CATEGORIES["sonarr"]: f"{QBITTORRENT_SHARED_DOWNLOAD_PATH}/tv-sonarr-imported",
    ARR_QBITTORRENT_IMPORTED_CATEGORIES["lidarr"]: f"{QBITTORRENT_SHARED_DOWNLOAD_PATH}/lidarr-imported",
    ARR_QBITTORRENT_IMPORTED_CATEGORIES["whisparr"]: f"{QBITTORRENT_SHARED_DOWNLOAD_PATH}/whisparr-imported",
}
QBITTORRENT_APP_PREFERENCE_DEFAULTS = {
    "queueing_enabled": True,
    "max_active_downloads": 8,
    "max_active_torrents": 12,
    "max_active_uploads": 8,
    "dont_count_slow_torrents": True,
    "slow_torrent_dl_rate_threshold": 102400,
    "slow_torrent_inactive_timer": 60,
}
ARR_SABNZBD_CATEGORIES = {
    "radarr": "movies",
    "sonarr": "tv",
    "lidarr": "music",
    "whisparr": "adult",
    "prowlarr": "prowlarr",
}
ARR_SABNZBD_CATEGORY_SAVE_PATHS = {
    ARR_SABNZBD_CATEGORIES["radarr"]: f"{SABNZBD_COMPLETE_DOWNLOAD_PATH}/movies",
    ARR_SABNZBD_CATEGORIES["sonarr"]: f"{SABNZBD_COMPLETE_DOWNLOAD_PATH}/tv",
    ARR_SABNZBD_CATEGORIES["lidarr"]: f"{SABNZBD_COMPLETE_DOWNLOAD_PATH}/music",
    ARR_SABNZBD_CATEGORIES["whisparr"]: f"{SABNZBD_COMPLETE_DOWNLOAD_PATH}/adult",
    ARR_SABNZBD_CATEGORIES["prowlarr"]: f"{SABNZBD_COMPLETE_DOWNLOAD_PATH}/prowlarr",
}
JELLYFIN_BOOTSTRAP_AUTH_HEADER = (
    'MediaBrowser Client="HaaC Bootstrap", Device="HaaC Bootstrap", DeviceId="haac-bootstrap", Version="1.0.0"'
)
JELLYFIN_DEFAULT_LIBRARIES = (
    {"name": "Movies", "collectionType": "movies", "path": "/data/movies"},
    {"name": "TV Shows", "collectionType": "tvshows", "path": "/data/tv"},
    {"name": "Music", "collectionType": "music", "path": "/data/music"},
    {"name": "Adult Movies", "collectionType": "movies", "path": "/data/adult"},
)
JELLYFIN_CONFIGURATION_DEFAULTS = {
    "UICulture": "it-IT",
    "MetadataCountryCode": "IT",
    "PreferredMetadataLanguage": "it",
}
ARR_DEFAULT_ROOT_FOLDERS = {
    "radarr": "/data/media/movies",
    "sonarr": "/data/media/tv",
    "lidarr": "/data/media/music",
    "whisparr": "/data/media/adult",
}
ARR_COMMON_NAMING_DEFAULTS = {
    "radarr": {
        "renameMovies": True,
        "standardMovieFormat": "{Movie CleanTitle} {(Release Year)} {imdb-{ImdbId}} {edition-{Edition Tags}} {[Custom Formats]}{[Quality Full]}{[MediaInfo 3D]}{[MediaInfo VideoDynamicRangeType]}{[Mediainfo AudioCodec}{ Mediainfo AudioChannels]}{[Mediainfo VideoCodec]}{-Release Group}",
        "movieFolderFormat": "{Movie CleanTitle} ({Release Year})",
    },
    "sonarr": {
        "renameEpisodes": True,
        "standardEpisodeFormat": "{Series TitleYear} - S{season:00}E{episode:00} - {Episode CleanTitle:90} {[Custom Formats]}{[Quality Full]}{[Mediainfo AudioCodec}{ Mediainfo AudioChannels]}{MediaInfo AudioLanguages}{[MediaInfo VideoDynamicRangeType]}{[Mediainfo VideoCodec]}{-Release Group}",
        "dailyEpisodeFormat": "{Series TitleYear} - {Air-Date} - {Episode CleanTitle:90} {[Custom Formats]}{[Quality Full]}{[Mediainfo AudioCodec}{ Mediainfo AudioChannels]}{MediaInfo AudioLanguages}{[MediaInfo VideoDynamicRangeType]}{[Mediainfo VideoCodec]}{-Release Group}",
        "animeEpisodeFormat": "{Series TitleYear} - S{season:00}E{episode:00} - {absolute:000} - {Episode CleanTitle:90} {[Custom Formats]}{[Quality Full]}{[Mediainfo AudioCodec}{ Mediainfo AudioChannels]}{MediaInfo AudioLanguages}{[MediaInfo VideoDynamicRangeType]}[{Mediainfo VideoCodec }{MediaInfo VideoBitDepth}bit]{-Release Group}",
        "seriesFolderFormat": "{Series TitleYear} [tvdbid-{TvdbId}]",
        "seasonFolderFormat": "Season {season:00}",
        "specialsFolderFormat": "Specials",
    },
    "lidarr": {
        "renameTracks": True,
        "standardTrackFormat": "{Album Title}/{track:00} - {Track Title}",
        "multiDiscTrackFormat": "{Album Title}/{Medium Format} {medium:00}/{track:00} - {Track Title}",
        "artistFolderFormat": "{Artist Name}",
        "includeArtistName": False,
        "includeAlbumTitle": False,
        "includeQuality": False,
        "replaceSpaces": False,
    },
    "whisparr": {
        "renameMovies": True,
        "standardMovieFormat": "{Movie CleanTitle} {(Release Year)} {imdb-{ImdbId}} {edition-{Edition Tags}} {[Custom Formats]}{[Quality Full]}{[MediaInfo 3D]}{[MediaInfo VideoDynamicRangeType]}{[Mediainfo AudioCodec}{ Mediainfo AudioChannels]}{[Mediainfo VideoCodec]}{-Release Group}",
        # Whisparr validates movie folders as a relative path segment beneath the root folder.
        "movieFolderFormat": "Movies/{Movie CleanTitle} ({Release Year})",
    },
}
ARR_COMMON_MEDIA_MANAGEMENT_DEFAULTS = {
    "deleteEmptyFolders": True,
    "setPermissionsLinux": True,
    "chmodFolder": "775",
    "copyUsingHardlinks": True,
}
ARR_COMMON_DOWNLOAD_CLIENT_DEFAULTS = {
    "enableCompletedDownloadHandling": True,
    "autoRedownloadFailed": True,
}
ARR_LANGUAGE_CODE_ALIASES = {
    "it": "Italian",
    "ita": "Italian",
    "italian": "Italian",
    "en": "English",
    "eng": "English",
    "english": "English",
}
ARR_LANGUAGE_PREFERENCE_DEFAULT = ("Italian", "English")
ARR_LANGUAGE_SCORE_OVERRIDES = {
    "Italian": 200,
    "English": 50,
}
ARR_LANGUAGE_CUSTOM_FORMAT_PREFIX = "HAAC Language: Prefer "
ARR_VERIFIER_CANDIDATES = (
    {"query": "The General", "title": "The General", "year": 1926, "tmdbId": 961},
    {"query": "His Girl Friday", "title": "His Girl Friday", "year": 1940, "tmdbId": 3085},
    {"query": "Nosferatu", "title": "Nosferatu", "year": 1922, "tmdbId": 653},
    {"query": "Night of the Living Dead", "title": "Night of the Living Dead", "year": 1968, "tmdbId": 10331},
    {"query": "Sita Sings the Blues", "title": "Sita Sings the Blues", "year": 2008, "tmdbId": 20529},
)
ARR_VERIFIER_PREFERRED_MAX_SIZE_BYTES = 2 * 1024 * 1024 * 1024
ARR_VERIFIER_POLL_SECONDS = 15
ARR_VERIFIER_AVOID_RELEASE_TOKENS = ("yts", "yify")
QBITTORRENT_WEBUI_HOST_HEADER = "127.0.0.1:8080"
UP_PHASE_ORDER = (
    "Preflight",
    "Infrastructure provisioning",
    "Node configuration",
    "GitOps publication",
    "GitOps readiness",
    "Cloudflare publication",
    "Cluster verification",
    "Public URL verification",
)
UP_PHASE_RANK = {phase: index for index, phase in enumerate(UP_PHASE_ORDER)}
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
LITMUS_DYNAMIC_METADATA_LABELS = {
    "workflow_id",
    "infra_id",
    "revision_id",
    "type",
    "workflows.argoproj.io/controller-instanceid",
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
    envdefaultslib.apply_identity_defaults(merged)
    if not merged.get("PROXMOX_HOST_PASSWORD") and merged.get("LXC_PASSWORD"):
        merged["PROXMOX_HOST_PASSWORD"] = merged["LXC_PASSWORD"]
    merged.setdefault("HAAC_FALCO_INGEST_NODEPORT", "32081")
    merged.setdefault("TRAEFIK_TRUSTED_IPS", TRAEFIK_DEFAULT_TRUSTED_IPS)
    if merged.get("GRAFANA_OIDC_SECRET"):
        merged.setdefault(
            "GRAFANA_OIDC_SECRET_SHA256",
            hashlib.sha256(merged["GRAFANA_OIDC_SECRET"].encode("utf-8")).hexdigest(),
        )
    if merged.get("QUI_PASSWORD"):
        merged.setdefault("QBITTORRENT_PASSWORD_PBKDF2", qbittorrent_password_pbkdf2(merged["QUI_PASSWORD"]))
        merged.setdefault(
            "DOWNLOADERS_AUTH_SECRET_SHA256",
            stable_secret_checksum(
                {
                    "QBITTORRENT_USERNAME": merged.get("QBITTORRENT_USERNAME", "admin"),
                    "QUI_PASSWORD": merged["QUI_PASSWORD"],
                    "QBITTORRENT_PASSWORD_PBKDF2": merged["QBITTORRENT_PASSWORD_PBKDF2"],
                }
            ),
        )
    if merged.get("PROTONVPN_OPENVPN_USERNAME") and merged.get("PROTONVPN_OPENVPN_PASSWORD"):
        merged.setdefault(
            "PROTONVPN_SECRET_SHA256",
            stable_secret_checksum(
                {
                    "OPENVPN_USER": protonvpn_port_forward_username(merged["PROTONVPN_OPENVPN_USERNAME"]),
                    "OPENVPN_PASSWORD": merged["PROTONVPN_OPENVPN_PASSWORD"],
                }
            ),
        )
    if merged.get("QUI_PASSWORD") and merged.get("GRAFANA_ADMIN_PASSWORD"):
        merged.setdefault(
            "HOMEPAGE_WIDGETS_SECRET_SHA256",
            stable_secret_checksum(
                {
                    "HOMEPAGE_VAR_GRAFANA_USERNAME": merged.get("GRAFANA_ADMIN_USERNAME", "admin"),
                    "HOMEPAGE_VAR_GRAFANA_PASSWORD": merged["GRAFANA_ADMIN_PASSWORD"],
                    "HOMEPAGE_VAR_QBITTORRENT_USERNAME": merged.get("QBITTORRENT_USERNAME", "admin"),
                    "HOMEPAGE_VAR_QBITTORRENT_PASSWORD": merged["QUI_PASSWORD"],
                }
            ),
        )
    if merged.get("CROWDSEC_BOUNCER_KEY"):
        dynamic_config = crowdsec_traefik_dynamic_config(merged)
        merged.setdefault(
            "CROWDSEC_TRAEFIK_SECRET_SHA256",
            stable_secret_checksum(
                {
                    "crowdsec-bouncer.yaml": dynamic_config,
                    "crowdsec-lapi-key": merged["CROWDSEC_BOUNCER_KEY"],
                }
            ),
        )
    merged.setdefault("HOMEPAGE_CONFIG_CHECKSUM", homepage_config_checksum(merged))
    return merged


def protonvpn_port_forward_username(username: str) -> str:
    raw = str(username or "").strip()
    if not raw:
        return ""
    parts = [part for part in raw.split("+") if part]
    base = parts[0]
    suffixes = [part for part in parts[1:] if part.lower() not in {"pmp", "nr"}]
    suffixes.append("pmp")
    return "+".join((base, *suffixes))


def stable_secret_checksum(values: dict[str, str]) -> str:
    payload = "\n".join(f"{key}={values[key]}" for key in sorted(values))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def trusted_ip_list(raw: str | None) -> list[str]:
    values: list[str] = []
    for item in str(raw or "").split(","):
        candidate = item.strip()
        if candidate and candidate not in values:
            values.append(candidate)
    return values


def crowdsec_traefik_dynamic_config(env: dict[str, str]) -> str:
    trusted_ips = trusted_ip_list(env.get("TRAEFIK_TRUSTED_IPS")) or trusted_ip_list(TRAEFIK_DEFAULT_TRUSTED_IPS)
    trusted_ip_lines = "\n".join(f"            - {cidr}" for cidr in trusted_ips)
    return (
        "http:\n"
        "  middlewares:\n"
        "    crowdsec-bouncer:\n"
        "      plugin:\n"
        "        crowdsec-bouncer-traefik-plugin:\n"
        "          enabled: true\n"
        "          logLevel: INFO\n"
        "          metricsUpdateIntervalSeconds: 60\n"
        "          crowdsecMode: stream\n"
        "          crowdsecLapiScheme: http\n"
        "          crowdsecLapiHost: crowdsec-service.crowdsec.svc.cluster.local:8080\n"
        "          crowdsecLapiKeyFile: /etc/traefik/crowdsec/auth/crowdsec-lapi-key\n"
        "          crowdsecAppsecEnabled: true\n"
        "          crowdsecAppsecHost: crowdsec-appsec-service.crowdsec.svc.cluster.local:7422\n"
        "          crowdsecAppsecFailureBlock: true\n"
        "          crowdsecAppsecUnreachableBlock: false\n"
        "          forwardedHeadersTrustedIPs:\n"
        f"{trusted_ip_lines}\n"
    )


def extract_top_level_yaml_section(content: str, section_name: str) -> str:
    lines = content.splitlines()
    header = f"{section_name}:"
    capture = False
    captured: list[str] = []
    top_level_key = re.compile(r"^[A-Za-z0-9_-]+:\s*(?:#.*)?$")
    for line in lines:
        if not capture:
            if line.startswith(header):
                capture = True
                captured.append(line)
            continue
        if line and not line.startswith((" ", "\t")) and top_level_key.match(line):
            break
        captured.append(line)
    return "\n".join(captured).strip()


def homepage_config_checksum(env: dict[str, str]) -> str:
    rendered_values = gitopslib.render_env_placeholders(VALUES_TEMPLATE.read_text(encoding="utf-8"), env)
    inputs = [
        extract_top_level_yaml_section(rendered_values, "ingresses"),
        extract_top_level_yaml_section(rendered_values, "homepage"),
    ]
    return hashlib.sha256("\n---\n".join(inputs).encode("utf-8")).hexdigest()


def qbittorrent_password_pbkdf2(password: str) -> str:
    salt = hashlib.sha256(f"haac-qbittorrent:{password}".encode("utf-8")).digest()[:16]
    derived = hashlib.pbkdf2_hmac("sha512", password.encode("utf-8"), salt, 100000, dklen=64)
    return f"@ByteArray({base64.b64encode(salt).decode()}:{base64.b64encode(derived).decode()})"


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


def strip_ip_cidr(value: str) -> str:
    return value.strip().split("/", 1)[0].strip()


def worker_nodes_config(env: dict[str, str]) -> list[tuple[str, dict[str, object]]]:
    worker_nodes_raw = env.get("WORKER_NODES_JSON", "").strip()
    if not worker_nodes_raw:
        return []

    try:
        worker_nodes = json.loads(worker_nodes_raw)
    except json.JSONDecodeError as exc:
        raise HaaCError("WORKER_NODES_JSON must be valid JSON before bootstrap can inspect worker identities") from exc

    if isinstance(worker_nodes, dict):
        entries = [(str(key), value) for key, value in worker_nodes.items()]
    elif isinstance(worker_nodes, list):
        entries = [(str(index), value) for index, value in enumerate(worker_nodes, start=1)]
    else:
        raise HaaCError("WORKER_NODES_JSON must decode to a JSON object or array")

    normalized: list[tuple[str, dict[str, object]]] = []
    for key, value in entries:
        if isinstance(value, dict):
            normalized.append((key, value))
    return normalized


def cluster_node_hosts(env: dict[str, str]) -> list[str]:
    hosts: list[str] = []
    master_host = strip_ip_cidr(env.get("K3S_MASTER_IP", ""))
    if master_host:
        hosts.append(master_host)

    for _, entry in worker_nodes_config(env):
        worker_host = strip_ip_cidr(str(entry.get("ip", "")))
        if worker_host:
            hosts.append(worker_host)

    return hosts


def proxmox_json(host: str, remote_command: str, *, connect_timeout: int = 5) -> dict | list:
    output = run_proxmox_ssh_stdout(host, remote_command, connect_timeout=connect_timeout)
    try:
        payload = json.loads(output) if output else []
    except json.JSONDecodeError as exc:
        raise HaaCError(f"Invalid JSON returned by Proxmox command: {remote_command}") from exc
    if isinstance(payload, (dict, list)):
        return payload
    raise HaaCError(f"Unexpected Proxmox JSON payload returned by: {remote_command}")


def proxmox_lxc_ipv4(config: dict[str, object]) -> str:
    for key, value in config.items():
        if not key.startswith("net") or not isinstance(value, str):
            continue
        match = re.search(r"(?:^|,)ip=([^,]+)", value)
        if not match:
            continue
        ip_value = strip_ip_cidr(match.group(1))
        if ip_value and ip_value.lower() != "dhcp":
            return ip_value
    return ""


def declared_k3s_lxc_identities(env: dict[str, str], tofu_dir: Path) -> list[dict[str, str]]:
    outputs = tofu_output_json(tofu_dir)
    identities: list[dict[str, str]] = []

    master_vmid = outputs.get("master_vmid", {}).get("value")
    master_hostname = env.get("LXC_MASTER_HOSTNAME", "").strip() or "haacarr-master"
    master_ip = strip_ip_cidr(env.get("K3S_MASTER_IP", "") or tofu_output_value(tofu_dir, "master_ip"))
    if master_vmid is not None and master_hostname and master_ip:
        identities.append(
            {
                "name": "master",
                "vmid": str(master_vmid),
                "hostname": master_hostname,
                "ip": master_ip,
            }
        )

    worker_configs = {name: item for name, item in worker_nodes_config(env)}
    worker_items = outputs.get("workers", {}).get("value", {})
    if isinstance(worker_items, dict):
        for worker_name, worker_output in worker_items.items():
            if not isinstance(worker_output, dict):
                continue
            worker_config = worker_configs.get(str(worker_name), {})
            hostname = str(worker_config.get("hostname", "")).strip() or str(worker_name).strip()
            worker_ip = strip_ip_cidr(str(worker_output.get("ip", "") or worker_config.get("ip", "")))
            vmid = worker_output.get("vmid")
            if vmid is None or not hostname or not worker_ip:
                continue
            identities.append(
                {
                    "name": str(worker_name),
                    "vmid": str(vmid),
                    "hostname": hostname,
                    "ip": worker_ip,
                }
            )

    return identities


def proxmox_lxc_resources(host: str) -> list[dict[str, str]]:
    payload = proxmox_json(host, "pvesh get /cluster/resources --type vm --output-format json")
    if not isinstance(payload, list):
        raise HaaCError("Proxmox cluster resources did not return a JSON list")

    resources: list[dict[str, str]] = []
    for item in payload:
        if not isinstance(item, dict) or str(item.get("type", "")).strip() != "lxc":
            continue
        vmid = item.get("vmid")
        if vmid is None:
            continue
        resources.append(
            {
                "vmid": str(vmid),
                "node": str(item.get("node", "")).strip(),
                "name": str(item.get("name", "")).strip(),
                "status": str(item.get("status", "")).strip(),
            }
        )
    return resources


def proxmox_lxc_config(host: str, node: str, vmid: str) -> dict[str, object]:
    payload = proxmox_json(
        host,
        f"pvesh get /nodes/{shlex.quote(node)}/lxc/{shlex.quote(vmid)}/config --output-format json",
    )
    if not isinstance(payload, dict):
        raise HaaCError(f"Proxmox config for LXC {vmid} did not return a JSON object")
    return payload


def find_duplicate_k3s_lxc_identities(
    proxmox_host: str,
    tofu_dir: Path,
    *,
    env: dict[str, str] | None = None,
) -> list[dict[str, object]]:
    working_env = env or merged_env()
    declared = declared_k3s_lxc_identities(working_env, tofu_dir)
    if not declared:
        return []

    declared_vmids = {item["vmid"] for item in declared}
    declared_hostnames = {item["hostname"]: item for item in declared if item.get("hostname")}
    declared_ips = {item["ip"]: item for item in declared if item.get("ip")}

    duplicates: list[dict[str, object]] = []
    for resource in proxmox_lxc_resources(proxmox_host):
        vmid = resource["vmid"]
        if vmid in declared_vmids:
            continue
        node = resource.get("node", "").strip()
        if not node:
            continue
        config = proxmox_lxc_config(proxmox_host, node, vmid)
        hostname = str(config.get("hostname", "")).strip() or resource.get("name", "")
        ipv4 = proxmox_lxc_ipv4(config)
        reasons: list[str] = []
        if hostname and hostname in declared_hostnames:
            reasons.append(f"hostname {hostname}")
        if ipv4 and ipv4 in declared_ips:
            reasons.append(f"IPv4 {ipv4}")
        if not reasons:
            continue
        duplicates.append(
            {
                **resource,
                "hostname": hostname,
                "ip": ipv4,
                "reasons": reasons,
            }
        )

    return duplicates


def quarantine_duplicate_k3s_lxc_identities(
    proxmox_host: str,
    tofu_dir: Path,
    *,
    env: dict[str, str] | None = None,
) -> list[dict[str, object]]:
    duplicates = find_duplicate_k3s_lxc_identities(proxmox_host, tofu_dir, env=env)
    if not duplicates:
        print("[ok] No duplicate unmanaged K3s LXC identities detected")
        return []

    for duplicate in duplicates:
        vmid = str(duplicate["vmid"])
        hostname = str(duplicate.get("hostname", "")).strip() or "<unknown>"
        reason = ", ".join(str(item) for item in duplicate.get("reasons", []))
        run_proxmox_ssh(proxmox_host, f"pct set {shlex.quote(vmid)} -onboot 0")
        if str(duplicate.get("status", "")).strip().lower() == "running":
            run_proxmox_ssh(proxmox_host, f"pct shutdown {shlex.quote(vmid)} --timeout 60", check=False)
        status_output = run_proxmox_ssh_stdout(proxmox_host, f"pct status {shlex.quote(vmid)}", check=False)
        if "status: stopped" not in status_output:
            run_proxmox_ssh(proxmox_host, f"pct stop {shlex.quote(vmid)}", check=False)
            status_output = run_proxmox_ssh_stdout(proxmox_host, f"pct status {shlex.quote(vmid)}", check=False)
        if "status: stopped" not in status_output:
            raise HaaCError(f"Unable to quarantine duplicate unmanaged LXC {vmid}: {status_output.strip() or 'unknown status'}")
        print(f"[heal] Quarantined unmanaged duplicate LXC {vmid} ({hostname}): {reason}")

    return duplicates


def replace_known_host_entries(path: Path, host: str, entries: str) -> None:
    existing_lines = path.read_text(encoding="utf-8").splitlines() if path.exists() else []
    retained: list[str] = []
    for line in existing_lines:
        if not line or line.startswith("#"):
            retained.append(line)
            continue
        marker = line.split(" ", 1)[0]
        if marker.startswith("|1|"):
            retained.append(line)
            continue
        known_markers = marker.split(",")
        if host in known_markers or f"[{host}]:22" in known_markers:
            continue
        retained.append(line)

    for entry in entries.splitlines():
        cleaned = entry.strip()
        if cleaned:
            retained.append(cleaned)

    rendered = "\n".join(retained)
    if rendered:
        rendered += "\n"
    path.write_text(rendered, encoding="utf-8")


def refresh_cluster_known_hosts(env: dict[str, str], *, timeout_seconds: int = 120) -> None:
    access_host = proxmox_access_host(env)
    local_known_hosts = known_hosts_path(env)
    for host in cluster_node_hosts(env):
        deadline = time.time() + timeout_seconds
        scanned_entries = ""
        while time.time() < deadline:
            scanned_entries = run_proxmox_ssh_stdout(
                access_host,
                f"ssh-keyscan -T 5 -t ed25519 {shlex.quote(host)} 2>/dev/null || true",
                connect_timeout=10,
                check=False,
            )
            if scanned_entries.strip():
                replace_known_host_entries(local_known_hosts, host, scanned_entries)
                break
            time.sleep(2)
        else:
            raise HaaCError(f"Timed out refreshing SSH host key for K3s node {host}")


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


def stash_tracked_git_changes(paths: list[str], *, message: str) -> str | None:
    if not paths:
        return None
    stashed = run(
        ["git", "stash", "push", "--message", message, "--", *paths],
        check=False,
        capture_output=True,
    )
    require_success(stashed, "Unable to preserve local tracked changes before sync")
    combined_output = "\n".join(part for part in ((stashed.stdout or "").strip(), (stashed.stderr or "").strip()) if part)
    if "No local changes to save" in combined_output:
        return None
    return "stash@{0}"


def restore_tracked_git_changes(stash_ref: str) -> None:
    applied = run(["git", "stash", "apply", "--index", stash_ref], check=False, capture_output=True)
    if applied.returncode != 0:
        detail = (applied.stderr or applied.stdout or "").strip()
        if detail:
            detail = f" Git reported: {detail}"
        raise HaaCError(
            "Sync updated the branch but could not restore the preserved local tracked changes cleanly. "
            f"Resolve the worktree manually and recover the preserved changes from `{stash_ref}` before rerunning `task sync`.{detail}"
        )
    dropped = run(["git", "stash", "drop", stash_ref], check=False, capture_output=True)
    require_success(dropped, "Unable to drop the temporary sync stash after restore")


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


def extract_up_recovery_summary(output_lines: list[str]) -> tuple[str, str, str] | None:
    failing_phase = ""
    last_verified_phase = ""
    rerun_guidance = ""
    for line in output_lines:
        failing_match = UP_RECOVERY_FAILING_PATTERN.match(line)
        if failing_match:
            failing_phase = failing_match.group(1).strip()
            continue
        last_verified_match = UP_RECOVERY_LAST_VERIFIED_PATTERN.match(line)
        if last_verified_match:
            last_verified_phase = last_verified_match.group(1).strip()
            continue
        rerun_match = UP_RECOVERY_RERUN_PATTERN.match(line)
        if rerun_match:
            rerun_guidance = rerun_match.group(1).strip()
    if failing_phase and last_verified_phase and rerun_guidance:
        return failing_phase, last_verified_phase, rerun_guidance
    return None


def emit_up_failure_summary(output_lines: list[str]) -> None:
    explicit_summary = extract_up_recovery_summary(output_lines)
    if explicit_summary:
        failing_phase, last_verified_phase, rerun_guidance = explicit_summary
        print(f"[recovery] Failing phase: {failing_phase}", file=sys.stderr)
        print(f"[recovery] Last verified phase: {last_verified_phase}", file=sys.stderr)
        print(f"[recovery] Full rerun guidance: {rerun_guidance}", file=sys.stderr)
        return

    phases: list[str] = []
    highest_phase_rank = -1
    for line in output_lines:
        match = UP_TASK_LINE_PATTERN.match(line)
        if not match:
            continue
        phase = infer_up_phase(match.group(1), match.group(2))
        if not phase:
            continue
        phase_rank = UP_PHASE_RANK.get(phase, -1)
        if phase_rank < highest_phase_rank:
            continue
        if phase_rank > highest_phase_rank:
            phases.append(phase)
            highest_phase_rank = phase_rank

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
        encoding="utf-8",
        errors="replace",
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
    runtime_id = env.get("HAAC_WSL_RUNTIME_ID", "").strip()
    if not runtime_id:
        runtime_id = f"pid-{os.getpid()}-tid-{threading.get_ident()}"
    safe_runtime_id = re.sub(r"[^A-Za-z0-9._-]+", "-", runtime_id)
    return f"{runtime_root.rstrip('/')}/{wsl_distro(env)}/{safe_runtime_id}"


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


def gitops_stage_paths() -> list[str]:
    return [str(SECRETS_DIR), *[str(path) for path in GITOPS_GENERATED_OUTPUTS]]


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
            "CROWDSEC_BOUNCER_KEY",
            "CLOUDFLARE_TUNNEL_TOKEN",
            "PROTONVPN_OPENVPN_USERNAME",
            "PROTONVPN_OPENVPN_PASSWORD",
            "PROTONVPN_SERVER_COUNTRIES",
            "NTFY_TOPIC",
            "ARGOCD_OIDC_SECRET",
            "QUI_PASSWORD",
            "GRAFANA_ADMIN_PASSWORD",
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
        crowdsec_bouncer_config = temp_dir / "crowdsec-bouncer.yaml"
        crowdsec_bouncer_config.write_text(crowdsec_traefik_dynamic_config(env), encoding="utf-8")
        crowdsec_bouncer_key = temp_dir / "crowdsec-lapi-key"
        crowdsec_bouncer_key.write_text(env["CROWDSEC_BOUNCER_KEY"], encoding="utf-8")
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
                "OPENVPN_USER": protonvpn_port_forward_username(env["PROTONVPN_OPENVPN_USERNAME"]),
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
            "crowdsec-keys",
            "crowdsec",
            CROWDSEC_LAPI_SECRET_OUTPUT,
            {"BOUNCER_KEY_traefik": env["CROWDSEC_BOUNCER_KEY"]},
            None,
        ),
        (
            "traefik-crowdsec-bouncer",
            "kube-system",
            CROWDSEC_TRAEFIK_SECRET_OUTPUT,
            None,
            {
                "crowdsec-bouncer.yaml": crowdsec_bouncer_config,
                "crowdsec-lapi-key": crowdsec_bouncer_key,
            },
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
                "QBITTORRENT_USERNAME": env.get("QBITTORRENT_USERNAME", "admin"),
                "QUI_PASSWORD": env["QUI_PASSWORD"],
                "QBITTORRENT_PASSWORD_PBKDF2": env["QBITTORRENT_PASSWORD_PBKDF2"],
            },
            None,
        ),
        (
            "homepage-widgets-secret",
            "mgmt",
            HOMEPAGE_WIDGETS_SECRET_OUTPUT,
            {
                "HOMEPAGE_VAR_GRAFANA_USERNAME": env.get("GRAFANA_ADMIN_USERNAME", "admin"),
                "HOMEPAGE_VAR_GRAFANA_PASSWORD": env["GRAFANA_ADMIN_PASSWORD"],
                "HOMEPAGE_VAR_QBITTORRENT_USERNAME": env.get("QBITTORRENT_USERNAME", "admin"),
                "HOMEPAGE_VAR_QBITTORRENT_PASSWORD": env["QUI_PASSWORD"],
            },
            None,
        ),
        (
            "grafana-admin-secret",
            "monitoring",
            SECRETS_DIR / "grafana-admin-sealed-secret.yaml",
            {
                "admin-user": env.get("GRAFANA_ADMIN_USERNAME", "admin"),
                "admin-password": env["GRAFANA_ADMIN_PASSWORD"],
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
            "litmus-mongodb-credentials",
            "chaos",
            LITMUS_MONGODB_SECRET_OUTPUT,
            {
                "mongodb-root-password": env["LITMUS_MONGODB_ROOT_PASSWORD"],
                "mongodb-replica-set-key": env["LITMUS_MONGODB_REPLICA_SET_KEY"],
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


def argocd_tracking_parent_application(app: dict[str, object]) -> str:
    metadata = app.get("metadata") or {}
    annotations = metadata.get("annotations") or {}
    tracking_id = str(annotations.get("argocd.argoproj.io/tracking-id") or "").strip()
    if not tracking_id:
        return ""
    match = re.match(
        r"^(?P<parent>[^:]+):(?P<group>[^/]+)/(?P<kind>[^:]+):(?P<namespace>[^/]+)/(?P<resource>[^/]+)$",
        tracking_id,
    )
    if not match:
        return ""
    name = str(metadata.get("name") or "").strip()
    if (
        match.group("group") != "argoproj.io"
        or match.group("kind") != "Application"
        or match.group("namespace") != "argocd"
        or match.group("resource") != name
    ):
        return ""
    parent = match.group("parent").strip()
    if not parent or parent == name:
        return ""
    return parent


def argocd_hook_wait_resource_ref(app: dict[str, object]) -> dict[str, str] | None:
    status = app.get("status") or {}
    operation_state = status.get("operationState") or {}
    if (operation_state.get("phase") or "").strip() != "Running":
        return None
    message = str(operation_state.get("message") or "").strip()
    match = re.search(r"waiting for completion of hook\s+([^\s]+)", message, flags=re.IGNORECASE)
    if not match:
        return None
    hook_ref = match.group(1).strip().rstrip(".,;:")
    parts = [part.strip() for part in hook_ref.split("/") if part.strip()]
    if len(parts) == 3:
        group, kind, name = parts
    elif len(parts) == 2:
        group = ""
        kind, name = parts
    else:
        return None
    return {"ref": hook_ref, "group": group, "kind": kind, "name": name}


def kubectl_resource_token(kind: str, group: str = "") -> str:
    token = re.sub(r"(?<!^)(?=[A-Z])", "-", kind).lower()
    return f"{token}.{group}" if group else token


def argocd_hook_resource_exists(
    kubectl: str,
    kubeconfig: Path,
    app: dict[str, object],
    hook_resource: dict[str, str],
) -> bool:
    destination = ((app.get("spec") or {}).get("destination") or {})
    namespace = str(destination.get("namespace") or "").strip()
    resource = kubectl_resource_token(hook_resource["kind"], hook_resource["group"])
    attempts: list[list[str]] = []
    if namespace:
        attempts.append(["get", resource, hook_resource["name"], "-n", namespace, "--ignore-not-found=true", "-o", "name"])
    attempts.append(["get", resource, hook_resource["name"], "--ignore-not-found=true", "-o", "name"])
    for command in attempts:
        completed = run([kubectl, "--kubeconfig", str(kubeconfig), *command], check=False, capture_output=True)
        if completed.returncode == 0 and (completed.stdout or "").strip():
            return True
    return False


def argocd_parent_manages_child_application(parent_app: dict[str, object], child_application: str) -> bool:
    resources = ((parent_app.get("status") or {}).get("resources") or [])
    for resource in resources:
        if str(resource.get("kind") or "").strip() != "Application":
            continue
        if str(resource.get("group") or "argoproj.io").strip() != "argoproj.io":
            continue
        if str(resource.get("namespace") or "argocd").strip() != "argocd":
            continue
        if str(resource.get("name") or "").strip() == child_application:
            return True
    return False


def argocd_application_has_resource_finalizer(app: dict[str, object]) -> bool:
    finalizers = {
        str(value).strip() for value in ((app.get("metadata") or {}).get("finalizers") or []) if str(value).strip()
    }
    return any(
        value == "resources-finalizer.argocd.argoproj.io"
        or value.startswith("resources-finalizer.argocd.argoproj.io/")
        for value in finalizers
    )


def wait_for_argocd_application_recreation(
    kubectl: str,
    kubeconfig: Path,
    application: str,
    *,
    original_uid: str,
    timeout_seconds: int,
    interval_seconds: int = 5,
) -> None:
    deadline = time.time() + timeout_seconds
    disruption_observed = False
    while time.time() < deadline:
        completed = run(
            [
                kubectl,
                "--kubeconfig",
                str(kubeconfig),
                "get",
                "application",
                application,
                "-n",
                "argocd",
                "-o",
                "json",
            ],
            check=False,
            capture_output=True,
        )
        if completed.returncode != 0:
            disruption_observed = True
            time.sleep(interval_seconds)
            continue
        payload = json.loads((completed.stdout or "").strip() or "{}")
        metadata = payload.get("metadata") or {}
        current_uid = str(metadata.get("uid") or "").strip()
        if current_uid and current_uid != original_uid:
            return
        if str(metadata.get("deletionTimestamp") or "").strip():
            disruption_observed = True
        if not current_uid and disruption_observed:
            time.sleep(interval_seconds)
            continue
        time.sleep(interval_seconds)
    raise HaaCError(f"Timeout waiting for ArgoCD application {application} recreation")


def recover_missing_hook_argocd_operation(
    kubectl: str,
    kubeconfig: Path,
    application: str,
    app: dict[str, object],
    *,
    deadline: float,
    gitops_repo_url: str | None,
) -> bool:
    hook_resource = argocd_hook_wait_resource_ref(app)
    if not hook_resource:
        return False

    status = app.get("status") or {}
    desired_revision = ((status.get("sync") or {}).get("revision") or "").strip()
    active_revision = (((app.get("operation") or {}).get("sync") or {}).get("revision") or "").strip()
    if desired_revision and active_revision and active_revision != desired_revision:
        return False
    if argocd_hook_resource_exists(kubectl, kubeconfig, app, hook_resource):
        return False

    parent_application = argocd_tracking_parent_application(app)
    if not parent_application or not gitops_repo_url:
        raise HaaCError(
            f"ArgoCD application {application} is stuck waiting on missing hook {hook_resource['ref']} at the current revision, "
            "but it is not a repo-managed child Application with a known parent. Manual intervention is required."
        )

    original_uid = str(((app.get("metadata") or {}).get("uid")) or "").strip()
    if not original_uid:
        raise HaaCError(
            f"ArgoCD application {application} is stuck waiting on missing hook {hook_resource['ref']}, "
            "but the current Application UID is unavailable for safe recycle verification. Manual intervention is required."
        )

    parent_app = kubectl_json(
        kubectl,
        kubeconfig,
        ["get", "application", parent_application, "-n", "argocd", "-o", "json"],
        context=f"Read parent ArgoCD application {parent_application}",
    )
    if argocd_application_repo_url(parent_app) != gitops_repo_url:
        raise HaaCError(
            f"ArgoCD application {application} is stuck waiting on missing hook {hook_resource['ref']}, "
            f"but parent Application {parent_application} is not managed from the current GitOps repository. Manual intervention is required."
        )
    if not argocd_parent_manages_child_application(parent_app, application):
        raise HaaCError(
            f"ArgoCD application {application} is stuck waiting on missing hook {hook_resource['ref']}, "
            f"but parent Application {parent_application} does not currently prove ownership of the child Application. Manual intervention is required."
        )

    if argocd_application_has_resource_finalizer(app):
        raise HaaCError(
            f"ArgoCD application {application} is stuck waiting on missing hook {hook_resource['ref']}, "
            "but the child Application still owns a resources finalizer and will not be recycled automatically. Manual intervention is required."
        )

    refresh_argocd_application(kubectl, kubeconfig, parent_application, hard=True)
    run(
        [
            kubectl,
            "--kubeconfig",
            str(kubeconfig),
            "delete",
            "application",
            application,
            "-n",
            "argocd",
            "--ignore-not-found=true",
            "--wait=false",
        ],
        check=False,
    )
    wait_for_argocd_application_recreation(
        kubectl,
        kubeconfig,
        application,
        original_uid=original_uid,
        timeout_seconds=min(180, seconds_remaining(deadline)),
    )
    print(
        f"[heal] Recycled repo-managed ArgoCD child Application {application} after missing hook "
        f"{hook_resource['ref']} under parent {parent_application}"
    )
    return True


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
        if recover_missing_hook_argocd_operation(
            kubectl,
            kubeconfig,
            application,
            app,
            deadline=deadline,
            gitops_repo_url=gitops_repo_url,
        ):
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
        current_revision = argocd_application_sync_revision(app) or "unknown"

        if sync_status == "Synced" and health_status == "Healthy" and revision_current:
            print(f"[ok] {stage_label}: {application} synced and healthy")
            return
        if not revision_current:
            refresh_argocd_application(kubectl, kubeconfig, application, hard=True)
            print(
                f"[wait] {stage_label}: {application} on stale revision "
                f"{current_revision[:12]} (sync={sync_status or 'Unknown'} health={health_status or 'Unknown'}) "
                f"while waiting for {expected_revision[:12]}"
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


def find_zero_replica_replicasets(
    kubectl: str,
    kubeconfig: Path,
    targets: dict[str, tuple[str, ...]] = SECURITY_SIGNAL_RESIDUE_TARGETS,
) -> dict[str, set[str]]:
    stale_by_namespace: dict[str, set[str]] = {}
    for namespace, prefixes in targets.items():
        payload = kubectl_json(
            kubectl,
            kubeconfig,
            ["get", "replicaset", "-n", namespace, "-o", "json"],
            context=f"Unable to read ReplicaSets in namespace {namespace}",
        )
        for item in payload.get("items") or []:
            if not isinstance(item, dict):
                continue
            metadata = item.get("metadata") or {}
            name = str(metadata.get("name") or "").strip()
            if not name:
                continue
            if not any(name.startswith(prefix) for prefix in prefixes):
                continue
            spec = item.get("spec") or {}
            status = item.get("status") or {}
            replicas = int(spec.get("replicas") or 0)
            ready_replicas = int(status.get("readyReplicas") or 0)
            available_replicas = int(status.get("availableReplicas") or 0)
            if replicas == 0 and ready_replicas == 0 and available_replicas == 0:
                stale_by_namespace.setdefault(namespace, set()).add(name)
    return stale_by_namespace


def report_targets_stale_replicaset(item: dict[str, object], stale_by_namespace: dict[str, set[str]]) -> str:
    metadata = item.get("metadata") or {}
    namespace = str(metadata.get("namespace") or "").strip()
    stale_names = stale_by_namespace.get(namespace) or set()
    if not stale_names:
        return ""

    scope = item.get("scope") or {}
    scope_kind = str(scope.get("kind") or "").strip()
    scope_name = str(scope.get("name") or "").strip()
    if scope_kind == "ReplicaSet" and scope_name in stale_names:
        return scope_name

    for owner in metadata.get("ownerReferences") or []:
        if not isinstance(owner, dict):
            continue
        owner_kind = str(owner.get("kind") or "").strip()
        owner_name = str(owner.get("name") or "").strip()
        if owner_kind == "ReplicaSet" and owner_name in stale_names:
            return owner_name
    return ""


def delete_namespaced_resource(
    kubectl: str,
    kubeconfig: Path,
    *,
    resource: str,
    namespace: str,
    name: str,
) -> None:
    completed = run(
        [
            kubectl,
            "--kubeconfig",
            str(kubeconfig),
            "delete",
            resource,
            name,
            "-n",
            namespace,
            "--ignore-not-found=true",
        ],
        check=False,
        capture_output=True,
    )
    require_success(completed, f"Unable to delete {resource} {namespace}/{name}")


def delete_stale_namespaced_records(
    kubectl: str,
    kubeconfig: Path,
    *,
    resource: str,
    namespaces: tuple[str, ...],
    stale_by_namespace: dict[str, set[str]],
) -> tuple[int, dict[str, set[str]]]:
    deleted = 0
    matched_by_namespace: dict[str, set[str]] = {}
    for namespace in namespaces:
        if not stale_by_namespace.get(namespace):
            continue
        payload = kubectl_json(
            kubectl,
            kubeconfig,
            ["get", resource, "-n", namespace, "-o", "json"],
            context=f"Unable to read {resource} in namespace {namespace}",
        )
        for item in payload.get("items") or []:
            if not isinstance(item, dict):
                continue
            stale_name = report_targets_stale_replicaset(item, stale_by_namespace)
            if not stale_name:
                continue
            metadata = item.get("metadata") or {}
            name = str(metadata.get("name") or "").strip()
            if not name:
                continue
            delete_namespaced_resource(kubectl, kubeconfig, resource=resource, namespace=namespace, name=name)
            deleted += 1
            matched_by_namespace.setdefault(namespace, set()).add(stale_name)
            print(f"[ok] Deleted stale {resource} {namespace}/{name} for zero-replica ReplicaSet {stale_name}")
    return deleted, matched_by_namespace


def merge_stale_targets(*sources: dict[str, set[str]]) -> dict[str, set[str]]:
    merged: dict[str, set[str]] = {}
    for source in sources:
        for namespace, names in source.items():
            if names:
                merged.setdefault(namespace, set()).update(names)
    return merged


def cleanup_security_signal_residue_in_session(
    kubectl: str,
    kubeconfig: Path,
    targets: dict[str, tuple[str, ...]] = SECURITY_SIGNAL_RESIDUE_TARGETS,
) -> dict[str, int]:
    stale_by_namespace = find_zero_replica_replicasets(kubectl, kubeconfig, targets)
    if not stale_by_namespace:
        print("[ok] No allowlisted zero-replica rollout residue detected for security signal cleanup")
        return {"policy_reports": 0, "trivy_reports": 0, "replicasets": 0}

    namespaces = tuple(targets)

    deleted_policy_reports, policy_residue = delete_stale_namespaced_records(
        kubectl,
        kubeconfig,
        resource="policyreport",
        namespaces=namespaces,
        stale_by_namespace=stale_by_namespace,
    )
    deleted_trivy_reports = 0
    trivy_residue: dict[str, set[str]] = {}
    for resource in TRIVY_NAMESPACED_REPORT_RESOURCES:
        deleted, matched = delete_stale_namespaced_records(
            kubectl,
            kubeconfig,
            resource=resource,
            namespaces=namespaces,
            stale_by_namespace=stale_by_namespace,
        )
        deleted_trivy_reports += deleted
        trivy_residue = merge_stale_targets(trivy_residue, matched)

    residue_targets = merge_stale_targets(policy_residue, trivy_residue)
    if not residue_targets:
        print("[ok] No report-backed security residue required rollout-history pruning")
        return {
            "policy_reports": deleted_policy_reports,
            "trivy_reports": deleted_trivy_reports,
            "replicasets": 0,
        }

    deleted_replicasets = 0
    for namespace, names in residue_targets.items():
        for name in sorted(names):
            delete_namespaced_resource(kubectl, kubeconfig, resource="replicaset", namespace=namespace, name=name)
            deleted_replicasets += 1
            print(f"[ok] Deleted zero-replica ReplicaSet residue {namespace}/{name}")

    return {
        "policy_reports": deleted_policy_reports,
        "trivy_reports": deleted_trivy_reports,
        "replicasets": deleted_replicasets,
    }


def cleanup_security_signal_residue(master_ip: str, proxmox_host: str, kubeconfig: Path, kubectl: str) -> dict[str, int]:
    with cluster_session(proxmox_host, master_ip, kubeconfig, kubectl) as session_kubeconfig:
        counts = cleanup_security_signal_residue_in_session(kubectl, session_kubeconfig)
    if any(counts.values()):
        print(
            "[ok] Security signal residue cleanup removed "
            f"{counts['policy_reports']} PolicyReports, "
            f"{counts['trivy_reports']} Trivy reports, and "
            f"{counts['replicasets']} zero-replica ReplicaSets"
        )
    return counts


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


def repo_owned_untracked_collisions(remote_ref: str) -> list[str]:
    remote_paths = gitstatelib.git_paths_at_ref(ROOT, remote_ref)
    return sorted(path for path in gitstatelib.git_untracked_paths(ROOT) if path in remote_paths)


def fetch_gitops_remote_revision(revision: str) -> str:
    remote_ref = f"origin/{revision}"
    fetch = run(["git", "fetch", "origin", revision], check=False, capture_output=True)
    require_success(fetch, f"Git fetch failed for {remote_ref}")
    return remote_ref


def warn_shared_credential_scope(env: dict[str, str]) -> None:
    main_username = env.get("HAAC_MAIN_USERNAME", "").strip()
    downloader_username = env.get("QBITTORRENT_USERNAME", "").strip()
    main_password = env.get("HAAC_MAIN_PASSWORD", "").strip()
    downloader_password = env.get("QUI_PASSWORD", "").strip()
    if envdefaultslib.shared_downloader_credentials_enabled(env):
        print(
            "[warn] HAAC_ENABLE_SHARED_DOWNLOADER_CREDENTIALS is enabled: "
            "qBittorrent and QUI inherit the main operator credentials when their dedicated downloader vars are unset."
        )
        return
    if main_username and downloader_username and main_username == downloader_username:
        print("[warn] QBITTORRENT_USERNAME currently matches HAAC_MAIN_USERNAME. This widens the auth blast radius.")
    if main_password and downloader_password and main_password == downloader_password:
        print("[warn] QUI_PASSWORD currently matches HAAC_MAIN_PASSWORD. This widens the auth blast radius.")


def sync_repo() -> None:
    env = merged_env()
    require_git_bootstrap_repo(env)
    revision = gitops_revision(env)

    remote_ref = fetch_gitops_remote_revision(revision)
    ref_state = gitstatelib.git_ref_state(ROOT, "HEAD", remote_ref)
    tracked_dirty_paths = gitstatelib.git_tracked_dirty_paths(ROOT)
    if ref_state == "equal":
        if tracked_dirty_paths:
            checkpoint_git_changes(
                "Auto-save before sync [skip ci]",
                empty_message="[ok] GitOps repo already checkpointed before sync.",
                paths=tracked_dirty_paths,
            )
        else:
            print("[ok] GitOps repo already checkpointed before sync.")
        print(f"[ok] GitOps repo already matches {remote_ref}; no merge needed.")
        return
    if ref_state == "behind":
        colliding_untracked = repo_owned_untracked_collisions(remote_ref)
        if colliding_untracked:
            preview = ", ".join(colliding_untracked[:5])
            suffix = "" if len(colliding_untracked) <= 5 else f" (+{len(colliding_untracked) - 5} more)"
            raise HaaCError(
                f"Git sync stopped because untracked local paths would be overwritten by {remote_ref}: {preview}{suffix}. "
                "Move or remove those files, then rerun `task sync`."
            )
        preserved_stash: str | None = None
        fast_forward_applied = False
        if tracked_dirty_paths:
            preserved_stash = stash_tracked_git_changes(
                tracked_dirty_paths,
                message="haac-sync-preserve-tracked",
            )
        try:
            fast_forward = run(["git", "merge", "--ff-only", remote_ref], check=False, capture_output=True)
            require_success(fast_forward, f"Fast-forward sync failed for {remote_ref}")
            fast_forward_applied = True
            if preserved_stash:
                restore_tracked_git_changes(preserved_stash)
                checkpoint_git_changes(
                    "Auto-save before sync [skip ci]",
                    empty_message="[ok] GitOps repo already checkpointed before sync.",
                    paths=tracked_dirty_paths,
                )
        except HaaCError:
            if preserved_stash and not fast_forward_applied:
                restore = run(["git", "stash", "pop", "--index", preserved_stash], check=False, capture_output=True)
                require_success(restore, "Unable to restore preserved local tracked changes after a failed fast-forward sync")
            raise
        print(f"[ok] GitOps repo fast-forwarded to {remote_ref}")
        return
    if ref_state == "ahead":
        if tracked_dirty_paths:
            checkpoint_git_changes(
                "Auto-save before sync [skip ci]",
                empty_message="[ok] GitOps repo already checkpointed before sync.",
                paths=tracked_dirty_paths,
            )
        else:
            print("[ok] GitOps repo already checkpointed before sync.")
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

    remote_ref = fetch_gitops_remote_revision(revision)
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
        stage_git_paths(gitops_stage_paths())

    if not git_has_staged_changes():
        print("[ok] GitOps output already converged; nothing new to publish.")
        publication_commit_created = False
    else:
        remote_ref = fetch_gitops_remote_revision(revision)
        ref_state = gitstatelib.git_ref_state(ROOT, "HEAD", remote_ref)
        if ref_state in {"behind", "diverged"}:
            raise HaaCError(
                "GitOps publication stopped because the remote branch moved before the publication commit was created. "
                f"Local HEAD is now {ref_state} relative to {remote_ref}. "
                "Run `task sync` first, then rerun the publish or bootstrap command."
            )
        published = run(["git", "commit", "-m", "Updated infrastructure [skip ci]", "--no-verify"], check=False, capture_output=True)
        require_success(published, "GitOps publication commit failed")
        print(f"[ok] GitOps publication commit: {run_stdout(['git', 'rev-parse', 'HEAD'])}")
        publication_commit_created = True

    pushed = run(["git", "push", "origin", revision], check=False, capture_output=True)
    if pushed.returncode != 0 and publication_commit_created:
        remote_ref = fetch_gitops_remote_revision(revision)
        race_state = gitstatelib.git_ref_state(ROOT, "HEAD", remote_ref)
        if race_state in {"behind", "diverged"}:
            unwind = run(["git", "reset", "--mixed", "HEAD~1"], check=False, capture_output=True)
            require_success(unwind, "Unable to unwind the auto-generated GitOps publication commit after the remote moved")
            raise HaaCError(
                "GitOps publication stopped because the remote branch moved during the final push. "
                "The auto-generated publication commit was unwound back into local generated changes. "
                "Run `task sync`, then rerun the publish or bootstrap command."
            )
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
                run(["git", "add", *gitops_stage_paths()], check=False)
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


def http_request_text(
    url: str,
    *,
    method: str = "GET",
    payload: dict[str, object] | None = None,
    headers: dict[str, str] | None = None,
    opener: urllib.request.OpenerDirector | None = None,
    timeout: int = 60,
) -> tuple[int, str]:
    data = None
    request_headers = dict(headers or {})
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        request_headers.setdefault("Content-Type", "application/json")
    request = urllib.request.Request(url, data=data, headers=request_headers, method=method)
    open_fn = opener.open if opener is not None else urllib.request.urlopen
    try:
        with open_fn(request, timeout=timeout) as response:
            return response.status, response.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read().decode("utf-8")
    except (urllib.error.URLError, http.client.RemoteDisconnected, ConnectionError, TimeoutError, OSError) as exc:
        raise HaaCError(f"HTTP request failed: {method} {url}\n{exc}") from exc


def form_field_value(value: object) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if value is None:
        return ""
    return str(value)


def http_request_form_text(
    url: str,
    *,
    method: str = "POST",
    fields: list[tuple[str, object]] | tuple[tuple[str, object], ...],
    headers: dict[str, str] | None = None,
    opener: urllib.request.OpenerDirector | None = None,
    timeout: int = 60,
) -> tuple[int, str]:
    encoded_fields = [(key, form_field_value(value)) for key, value in fields]
    request_headers = dict(headers or {})
    request_headers.setdefault("Content-Type", "application/x-www-form-urlencoded")
    data = urllib.parse.urlencode(encoded_fields, doseq=True).encode("utf-8")
    request = urllib.request.Request(url, data=data, headers=request_headers, method=method)
    open_fn = opener.open if opener is not None else urllib.request.urlopen
    try:
        with open_fn(request, timeout=timeout) as response:
            return response.status, response.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read().decode("utf-8")
    except (urllib.error.URLError, http.client.RemoteDisconnected, ConnectionError, TimeoutError, OSError) as exc:
        raise HaaCError(f"HTTP form request failed: {method} {url}\n{exc}") from exc


def http_request_json(
    url: str,
    *,
    method: str = "GET",
    payload: dict[str, object] | None = None,
    headers: dict[str, str] | None = None,
    opener: urllib.request.OpenerDirector | None = None,
    timeout: int = 60,
) -> dict[str, object] | list[object]:
    status, body = http_request_text(
        url,
        method=method,
        payload=payload,
        headers=headers,
        opener=opener,
        timeout=timeout,
    )
    if status < 200 or status >= 300:
        raise HaaCError(f"API request failed: {method} {url}\nHTTP {status}\n{body}")
    try:
        parsed = json.loads(body)
    except json.JSONDecodeError as exc:
        raise HaaCError(f"API returned non-JSON content: {method} {url}") from exc
    if isinstance(parsed, (dict, list)):
        return parsed
    raise HaaCError(f"API returned unsupported JSON content: {method} {url}")


def build_cookie_opener() -> urllib.request.OpenerDirector:
    jar = http.cookiejar.CookieJar()
    return urllib.request.build_opener(urllib.request.HTTPCookieProcessor(jar))


def json_array(value: dict[str, object] | list[object]) -> list[dict[str, object]]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, dict)]


def json_object(value: dict[str, object] | list[object]) -> dict[str, object]:
    if isinstance(value, dict):
        return value
    return {}


def xml_element_text(root: ET.Element, name: str) -> str:
    for element in root.iter():
        local_name = element.tag.split("}", 1)[-1]
        if local_name == name and element.text:
            return element.text.strip()
    return ""


def wait_for_rollout(
    kubectl: str,
    kubeconfig: Path,
    *,
    namespace: str,
    resource: str,
    timeout_seconds: int = 600,
) -> None:
    run(
        [
            kubectl,
            "--kubeconfig",
            str(kubeconfig),
            "rollout",
            "status",
            resource,
            "-n",
            namespace,
            f"--timeout={timeout_seconds}s",
        ]
    )


def latest_pod_name(kubectl: str, kubeconfig: Path, namespace: str, selector: str) -> str:
    pod_name = run_stdout(
        [
            kubectl,
            "--kubeconfig",
            str(kubeconfig),
            "get",
            "pod",
            "-n",
            namespace,
            "-l",
            selector,
            "--sort-by=.metadata.creationTimestamp",
            "-o",
            "jsonpath={.items[-1].metadata.name}",
        ],
        check=False,
    )
    if not pod_name:
        raise HaaCError(f"No pod found in namespace {namespace} for selector {selector}")
    return pod_name


def kubectl_exec_stdout(
    kubectl: str,
    kubeconfig: Path,
    *,
    namespace: str,
    pod: str,
    container: str | None = None,
    script: str,
) -> str:
    command = [kubectl, "--kubeconfig", str(kubeconfig), "exec", "-n", namespace, pod]
    if container:
        command.extend(["-c", container])
    command.extend(["--", "/bin/sh", "-ec", script])
    return run_stdout(command)


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
    except (urllib.error.URLError, http.client.RemoteDisconnected, ConnectionError, TimeoutError, OSError) as exc:
        raise HaaCError(f"Litmus login probe transport failed: {exc}") from exc


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
LITMUS_CORE_DEPLOYMENTS = (
    "litmus-auth-server",
    "litmus-server",
)
LITMUS_TRANSIENT_ERROR_SNIPPETS = (
    "remote end closed connection without response",
    "connection refused",
    "connection reset by peer",
    "lost connection to pod",
    "timed out waiting for local port",
)


def litmus_is_transient_error(exc: BaseException) -> bool:
    if isinstance(exc, (urllib.error.URLError, http.client.RemoteDisconnected, ConnectionError, TimeoutError, OSError)):
        return True
    return any(snippet in str(exc).lower() for snippet in LITMUS_TRANSIENT_ERROR_SNIPPETS)


def retry_litmus_transient(
    action,
    *,
    context: str,
    attempts: int = 6,
    sleep_seconds: int = 5,
):
    for attempt in range(1, attempts + 1):
        try:
            return action()
        except Exception as exc:  # noqa: BLE001 - bounded retry on known Litmus warmup failures
            if not litmus_is_transient_error(exc):
                raise
            if attempt >= attempts:
                raise HaaCError(f"{context} failed after {attempts} attempts: {exc}") from exc
            print(
                f"[wait] {context}: transient Litmus service failure ({exc}); "
                f"retrying in {sleep_seconds}s ({attempt}/{attempts})"
            )
            time.sleep(sleep_seconds)


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
    except (urllib.error.URLError, http.client.RemoteDisconnected, ConnectionError, TimeoutError, OSError) as exc:
        raise HaaCError(f"Litmus API request failed: {method} {url}\n{exc}") from exc
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


def normalize_multiline_text(value: str) -> str:
    return "\n".join(line.rstrip() for line in value.strip().splitlines())


def require_path_within(root: Path, candidate: Path, *, description: str) -> Path:
    resolved_root = root.resolve()
    resolved_candidate = candidate.resolve()
    try:
        resolved_candidate.relative_to(resolved_root)
    except ValueError as exc:
        raise HaaCError(f"{description} escapes the Litmus chaos catalog root: {resolved_candidate}") from exc
    return resolved_candidate


def normalize_string_list(values: object) -> list[str]:
    if values is None:
        return []
    if not isinstance(values, list):
        raise HaaCError(f"Expected a JSON array of strings, got: {values!r}")
    normalized: list[str] = []
    for item in values:
        value = str(item).strip()
        if value:
            normalized.append(value)
    return sorted(dict.fromkeys(normalized))


def litmus_catalog_entry_id(name: str) -> str:
    return str(uuid.uuid5(uuid.NAMESPACE_URL, f"https://nucleoautogenerativo.it/haac/litmus/{name.strip()}"))


def canonicalize_litmus_manifest(manifest: str) -> str:
    raw = manifest.strip()
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError:
        return normalize_multiline_text(raw)
    if not isinstance(payload, dict):
        return json.dumps(payload, sort_keys=True, separators=(",", ":"))

    metadata = payload.get("metadata")
    if isinstance(metadata, dict):
        labels = metadata.get("labels")
        if isinstance(labels, dict):
            for key in LITMUS_DYNAMIC_METADATA_LABELS:
                labels.pop(key, None)
            if not labels:
                metadata.pop("labels", None)
    return json.dumps(payload, sort_keys=True, separators=(",", ":"))


def load_litmus_chaos_catalog(index_path: Path = LITMUS_CHAOS_CATALOG_INDEX) -> list[dict[str, object]]:
    catalog_root = index_path.parent.resolve()
    try:
        payload = json.loads(index_path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise HaaCError(f"Litmus chaos catalog index is missing: {index_path}") from exc
    except json.JSONDecodeError as exc:
        raise HaaCError(f"Litmus chaos catalog index is invalid JSON: {index_path}\n{exc}") from exc

    experiments = payload.get("experiments")
    if not isinstance(experiments, list) or not experiments:
        raise HaaCError(f"Litmus chaos catalog index must define a non-empty experiments list: {index_path}")

    catalog: list[dict[str, object]] = []
    for item in experiments:
        if not isinstance(item, dict):
            raise HaaCError(f"Litmus chaos catalog entry is not an object: {item!r}")
        name = str(item.get("name") or "").strip()
        description = str(item.get("description") or "").strip()
        manifest_name = str(item.get("manifest") or "").strip()
        source_manifest_name = str(item.get("sourceManifest") or "").strip()
        if not name or not description or not manifest_name:
            raise HaaCError(f"Litmus chaos catalog entry is missing name, description, or manifest: {item!r}")
        manifest_path = require_path_within(catalog_root, index_path.parent / manifest_name, description="Litmus chaos manifest path")
        try:
            manifest = manifest_path.read_text(encoding="utf-8").strip()
        except FileNotFoundError as exc:
            raise HaaCError(f"Litmus chaos manifest is missing: {manifest_path}") from exc
        if not manifest:
            raise HaaCError(f"Litmus chaos manifest is empty: {manifest_path}")

        source_manifest = ""
        source_manifest_path = ""
        if source_manifest_name:
            resolved_source_manifest_path = require_path_within(
                catalog_root,
                index_path.parent / source_manifest_name,
                description="Litmus source manifest path",
            )
            try:
                source_manifest = resolved_source_manifest_path.read_text(encoding="utf-8").strip()
            except FileNotFoundError as exc:
                raise HaaCError(f"Litmus source manifest is missing: {resolved_source_manifest_path}") from exc
            if not source_manifest:
                raise HaaCError(f"Litmus source manifest is empty: {resolved_source_manifest_path}")
            source_manifest_path = str(resolved_source_manifest_path)

        supporting_manifest_paths: list[str] = []
        for manifest_item in normalize_string_list(item.get("supportingManifests")):
            resolved_supporting_manifest_path = require_path_within(
                catalog_root,
                index_path.parent / manifest_item,
                description="Litmus supporting manifest path",
            )
            if not resolved_supporting_manifest_path.exists():
                raise HaaCError(f"Litmus supporting manifest is missing: {resolved_supporting_manifest_path}")
            supporting_manifest_paths.append(str(resolved_supporting_manifest_path))
        catalog.append(
            {
                "name": name,
                "description": description,
                "manifest": manifest,
                "manifest_path": str(manifest_path),
                "source_manifest": source_manifest,
                "source_manifest_path": source_manifest_path,
                "supporting_manifest_paths": supporting_manifest_paths,
                "tags": normalize_string_list(item.get("tags")),
            }
        )
    return catalog


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


def litmus_list_experiments(server_port: int, token: str, project_id: str) -> list[dict[str, object]]:
    data = litmus_graphql(
        server_port,
        token,
        (
            "query listExperiment($projectID: ID!, $request: ListExperimentRequest!) "
            "{ listExperiment(projectID: $projectID, request: $request) "
            "{ totalNoOfExperiments experiments { experimentID name description tags experimentManifest infra { infraID } } } }"
        ),
        {"projectID": project_id, "request": {}},
    )
    payload = data.get("listExperiment") or {}
    experiments = payload.get("experiments") or []
    return [item for item in experiments if isinstance(item, dict)]


def litmus_save_experiment(
    server_port: int,
    token: str,
    *,
    project_id: str,
    experiment_id: str,
    infra_id: str,
    name: str,
    description: str,
    manifest: str,
    tags: list[str],
) -> str:
    data = litmus_graphql(
        server_port,
        token,
        (
            "mutation saveChaosExperiment($projectID: ID!, $request: SaveChaosExperimentRequest!) "
            "{ saveChaosExperiment(request: $request, projectID: $projectID) }"
        ),
        {
            "projectID": project_id,
            "request": {
                "id": experiment_id,
                "name": name,
                "description": description,
                "tags": tags,
                "infraID": infra_id,
                "manifest": manifest,
            },
        },
    )
    saved = data.get("saveChaosExperiment")
    if not isinstance(saved, str) or not saved.strip():
        raise HaaCError(f"Litmus did not acknowledge the saved chaos experiment payload for {name}")
    return saved.strip()


def validate_litmus_supporting_manifest(manifest: str, manifest_path: Path) -> None:
    if not re.search(r"(?m)^[ \t]*kind:\s*ChaosExperiment\s*$", manifest):
        raise HaaCError(f"Litmus supporting manifest must define kind ChaosExperiment: {manifest_path}")
    if not re.search(r"(?m)^[ \t]*namespace:\s*litmus\s*$", manifest):
        raise HaaCError(f"Litmus supporting manifest must target namespace litmus: {manifest_path}")


def ensure_litmus_supporting_manifests(kubectl: str, kubeconfig: Path, catalog: list[dict[str, object]]) -> None:
    applied: set[str] = set()
    for entry in catalog:
        for manifest_path_text in entry.get("supporting_manifest_paths") or []:
            manifest_path = Path(str(manifest_path_text))
            if str(manifest_path) in applied:
                continue
            manifest = manifest_path.read_text(encoding="utf-8").strip()
            if not manifest:
                raise HaaCError(f"Litmus supporting manifest is empty: {manifest_path}")
            validate_litmus_supporting_manifest(manifest, manifest_path)
            run([kubectl, "--kubeconfig", str(kubeconfig), "apply", "-f", "-"], input_text=manifest)
            applied.add(str(manifest_path))
            print(f"[ok] Litmus supporting manifest applied: {manifest_path.name}")


def ensure_litmus_chaos_catalog(
    server_port: int,
    token: str,
    project_id: str,
    *,
    infra_id: str,
    kubectl: str,
    kubeconfig: Path,
) -> None:
    catalog = load_litmus_chaos_catalog()
    ensure_litmus_supporting_manifests(kubectl, kubeconfig, catalog)
    existing = litmus_list_experiments(server_port, token, project_id)
    existing_by_name: dict[str, dict[str, object]] = {}
    for item in existing:
        name = str(item.get("name") or "").strip()
        if name and name not in existing_by_name:
            existing_by_name[name] = item

    for entry in catalog:
        name = str(entry["name"])
        manifest = str(entry["manifest"])
        description = str(entry["description"])
        tags = list(entry.get("tags") or [])
        current = existing_by_name.get(name)
        if current:
            current_manifest = canonicalize_litmus_manifest(str(current.get("experimentManifest") or ""))
            current_description = str(current.get("description") or "").strip()
            current_tags = normalize_string_list(current.get("tags"))
            current_infra = str(((current.get("infra") or {}).get("infraID") or "")).strip()
            if (
                current_manifest == canonicalize_litmus_manifest(manifest)
                and current_description == description
                and current_tags == tags
                and current_infra == infra_id
            ):
                print(f"[ok] Litmus chaos experiment already seeded: {name}")
                continue

            litmus_save_experiment(
                server_port,
                token,
                project_id=project_id,
                experiment_id=str(current.get("experimentID") or litmus_catalog_entry_id(name)),
                infra_id=infra_id,
                name=name,
                description=description,
                manifest=manifest,
                tags=tags,
            )
            print(f"[ok] Litmus chaos experiment updated: {name}")
            continue

        litmus_save_experiment(
            server_port,
            token,
            project_id=project_id,
            experiment_id=litmus_catalog_entry_id(name),
            infra_id=infra_id,
            name=name,
            description=description,
            manifest=manifest,
            tags=tags,
        )
        print(f"[ok] Litmus chaos experiment seeded: {name}")


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


def wait_for_litmus_core_rollout(kubectl: str, kubeconfig: Path) -> None:
    for deployment in LITMUS_CORE_DEPLOYMENTS:
        run(
            [
                kubectl,
                "--kubeconfig",
                str(kubeconfig),
                "rollout",
                "status",
                f"deployment/{deployment}",
                "-n",
                "chaos",
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
) -> dict[str, object]:
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
        return active

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
    return active


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
    password = env.get("LITMUS_ADMIN_PASSWORD")
    if not password:
        print("[skip] Litmus chaos reconciliation skipped: no LITMUS_ADMIN_PASSWORD configured")
        return

    with cluster_session(proxmox_host, master_ip, kubeconfig, kubectl) as session_kubeconfig:
        if run([kubectl, "--kubeconfig", str(session_kubeconfig), "get", "deploy", "litmus-auth-server", "-n", "chaos"], check=False).returncode != 0:
            print("[skip] Litmus chaos reconciliation skipped: litmus-auth-server deployment is not present")
            return
        if run([kubectl, "--kubeconfig", str(session_kubeconfig), "get", "deploy", "litmus-server", "-n", "chaos"], check=False).returncode != 0:
            print("[skip] Litmus chaos reconciliation skipped: litmus-server deployment is not present")
            return
        wait_for_litmus_core_rollout(kubectl, session_kubeconfig)
        reconcile_litmus_admin_session(kubectl, session_kubeconfig, username=username, password=password)

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
            ["get", "secret", LITMUS_MONGODB_SECRET_NAME, "-n", "chaos", "-o", "json"],
            context="Unable to read Litmus MongoDB secret",
        )
        mongodb_data = decode_secret_data(mongodb_secret)
        mongodb_root_password = mongodb_data.get("mongodb-root-password")
        if not mongodb_root_password:
            raise HaaCError(f"Litmus MongoDB root password is missing from secret {LITMUS_MONGODB_SECRET_NAME}")
        mongo_uri = (
            "mongodb://root:"
            f"{urllib.parse.quote(mongodb_root_password, safe='')}"
            "@127.0.0.1:27017/admin?authSource=admin"
        )

        def reconcile_chaos_api() -> None:
            with kubectl_port_forward(kubectl, session_kubeconfig, "chaos", "svc/litmus-auth-server-service", auth_port) as auth_pf, kubectl_port_forward(
                kubectl, session_kubeconfig, "chaos", "svc/litmus-server-service", server_port
            ) as server_pf:
                login = litmus_auth_login(auth_pf, username, password)
                project_id = str(login["projectID"])
                token = str(login["accessToken"])

                environments = litmus_list_environments(server_pf, token, project_id)
                targets = select_litmus_reconcile_targets(environments)
                active_infra_id = ""
                for environment_id, environment_name, should_create_environment in targets:
                    active_infra = reconcile_litmus_environment_target(
                        server_pf,
                        token,
                        project_id,
                        environment_id,
                        environment_name,
                        should_create_environment=should_create_environment,
                        kubectl=kubectl,
                        kubeconfig=session_kubeconfig,
                    )
                    resolved_infra_id = str(active_infra.get("infraID") or "").strip()
                    if resolved_infra_id:
                        active_infra_id = resolved_infra_id
                if any(str(item.get("environmentID") or "") == LITMUS_LEGACY_ENVIRONMENT_ID for item in environments):
                    if litmus_hide_legacy_environment(kubectl, session_kubeconfig, mongo_uri, username=username):
                        print("[ok] Litmus legacy test environment hidden after canonical environment bootstrap")
                    else:
                        print("[ok] Litmus legacy test environment already hidden")
                if not active_infra_id:
                    raise HaaCError("Litmus chaos reconciliation did not resolve an active infra ID for the default environment")
                ensure_litmus_chaos_catalog(
                    server_pf,
                    token,
                    project_id,
                    infra_id=active_infra_id,
                    kubectl=kubectl,
                    kubeconfig=session_kubeconfig,
                )

        retry_litmus_transient(reconcile_chaos_api, context="Litmus chaos API reconciliation")


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


def reconcile_litmus_admin_session(kubectl: str, kubeconfig: Path, *, username: str, password: str) -> None:
    wait_for_litmus_core_rollout(kubectl, kubeconfig)

    service = kubectl_json(
        kubectl,
        kubeconfig,
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
        kubeconfig,
        ["get", "secret", LITMUS_MONGODB_SECRET_NAME, "-n", "chaos", "-o", "json"],
        context="Unable to read Litmus MongoDB secret",
    )
    mongodb_data = decode_secret_data(mongodb_secret)
    mongodb_root_password = mongodb_data.get("mongodb-root-password")
    if not mongodb_root_password:
        raise HaaCError(f"Litmus MongoDB root password is missing from secret {LITMUS_MONGODB_SECRET_NAME}")
    mongo_uri = (
        "mongodb://root:"
        f"{urllib.parse.quote(mongodb_root_password, safe='')}"
        "@127.0.0.1:27017/admin?authSource=admin"
    )

    def login_probe_status() -> tuple[int, str]:
        with kubectl_port_forward(kubectl, kubeconfig, "chaos", "svc/litmus-auth-server-service", auth_port) as port:
            return litmus_login_probe(port, username, password)

    status, _ = retry_litmus_transient(login_probe_status, context="Litmus admin login probe")
    if status not in {200, 401}:
        raise HaaCError(f"Unexpected Litmus login probe status before repair: {status}")
    if status == 401:
        delete_script = f'db.getSiblingDB("auth").users.deleteOne({{username:{json.dumps(username)}}})'
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
                delete_script,
            ]
        )
        run([kubectl, "--kubeconfig", str(kubeconfig), "rollout", "restart", "deployment/litmus-auth-server", "-n", "chaos"])
        run(
            [
                kubectl,
                "--kubeconfig",
                str(kubeconfig),
                "rollout",
                "status",
                "deployment/litmus-auth-server",
                "-n",
                "chaos",
                "--timeout=180s",
            ]
        )
        status, _ = retry_litmus_transient(login_probe_status, context="Litmus admin login probe after repair")
        if status != 200:
            raise HaaCError(f"Litmus admin credentials still failed after repair: login probe returned {status}")
        print("[ok] Litmus admin credentials reconciled from the repo-managed secret")
    else:
        print("[ok] Litmus admin credentials already match the repo-managed secret")

    litmus_clear_initial_login(kubectl, kubeconfig, mongo_uri, username=username)
    print("[ok] Litmus admin initial-login gate cleared")


def reconcile_litmus_admin(master_ip: str, proxmox_host: str, kubeconfig: Path, kubectl: str) -> None:
    env = merged_env()
    username = env.get("LITMUS_ADMIN_USERNAME", "admin")
    password = env.get("LITMUS_ADMIN_PASSWORD")
    if not password:
        print("[skip] Litmus admin reconciliation skipped: no LITMUS_ADMIN_PASSWORD configured")
        return

    with cluster_session(proxmox_host, master_ip, kubeconfig, kubectl) as session_kubeconfig:
        if run([kubectl, "--kubeconfig", str(session_kubeconfig), "get", "deploy", "litmus-auth-server", "-n", "chaos"], check=False).returncode != 0:
            print("[skip] Litmus admin reconciliation skipped: litmus-auth-server deployment is not present")
            return
        reconcile_litmus_admin_session(kubectl, session_kubeconfig, username=username, password=password)


def parse_bool(value: str) -> bool:
    return value.strip().lower() in {"1", "true", "yes", "on"}


def load_endpoint_specs(domain_name: str) -> list[dict[str, str]]:
    try:
        return endpointlib.load_endpoint_specs(VALUES_OUTPUT, VALUES_TEMPLATE, domain_name)
    except RuntimeError as exc:
        raise HaaCError(str(exc)) from exc


def probe_web_status(url: str, timeout_seconds: int = 10) -> int:
    return endpointlib.probe_web_status(url, timeout_seconds)


def parse_cloudflare_trace_ip(body: str) -> str:
    for line in body.splitlines():
        key, separator, value = line.partition("=")
        if separator and key.strip() == "ip":
            candidate = value.strip()
            try:
                ipaddress.ip_address(candidate)
            except ValueError:
                return ""
            return candidate
    return ""


def detect_public_ip(timeout_seconds: int = 10) -> str:
    probes = (
        ("https://www.cloudflare.com/cdn-cgi/trace", parse_cloudflare_trace_ip),
        ("https://api.ipify.org", lambda body: body.strip()),
    )
    headers = {"User-Agent": "haac-verify-web/1.0", "Accept": "text/plain"}
    for url, parser in probes:
        try:
            request = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
                body = response.read(4096).decode("utf-8", errors="replace")
        except Exception:
            continue
        candidate = parser(body)
        if not candidate:
            continue
        try:
            ipaddress.ip_address(candidate)
        except ValueError:
            continue
        return candidate
    return ""


OPERATOR_CROWDSEC_FALSE_POSITIVE_SCENARIOS = {
    "crowdsecurity/crowdsec-appsec-outofband",
    "crowdsecurity/http-crawl-non_statics",
    "LePresidente/http-generic-403-bf",
}


def crowdsec_has_operator_probe_ban(decisions_payload: object, source_ip: str) -> bool:
    if not isinstance(decisions_payload, list):
        return False
    for alert in decisions_payload:
        if not isinstance(alert, dict):
            continue
        if str(alert.get("scenario") or "") not in OPERATOR_CROWDSEC_FALSE_POSITIVE_SCENARIOS:
            continue
        for decision in alert.get("decisions") or []:
            if not isinstance(decision, dict):
                continue
            if str(decision.get("scope") or "").lower() == "ip" and str(decision.get("value") or "") == source_ip:
                return True
    return False


def crowdsec_operator_probe_ban_ips(decisions_payload: object) -> set[str]:
    candidates: set[str] = set()
    if not isinstance(decisions_payload, list):
        return candidates
    for alert in decisions_payload:
        if not isinstance(alert, dict):
            continue
        if str(alert.get("scenario") or "") not in OPERATOR_CROWDSEC_FALSE_POSITIVE_SCENARIOS:
            continue
        for decision in alert.get("decisions") or []:
            if not isinstance(decision, dict):
                continue
            if str(decision.get("scope") or "").lower() == "ip":
                value = str(decision.get("value") or "").strip()
                if value:
                    candidates.add(value)
    return candidates


def crowdsec_operator_probe_ban_scenarios(decisions_payload: object, source_ip: str) -> set[str]:
    candidates: set[str] = set()
    if not isinstance(decisions_payload, list):
        return candidates
    for alert in decisions_payload:
        if not isinstance(alert, dict):
            continue
        scenario = str(alert.get("scenario") or "").strip()
        if scenario not in OPERATOR_CROWDSEC_FALSE_POSITIVE_SCENARIOS:
            continue
        for decision in alert.get("decisions") or []:
            if not isinstance(decision, dict):
                continue
            if str(decision.get("scope") or "").lower() == "ip" and str(decision.get("value") or "").strip() == source_ip:
                candidates.add(scenario)
                break
    return candidates


def clear_operator_crowdsec_probe_ban(
    master_ip: str,
    proxmox_host: str,
    kubeconfig: Path,
    kubectl: str,
    source_ip: str,
) -> bool:
    with cluster_session(proxmox_host, master_ip, kubeconfig, kubectl) as session_kubeconfig:
        pod_name = run_stdout(
            [
                kubectl,
                "--kubeconfig",
                str(session_kubeconfig),
                "-n",
                "crowdsec",
                "get",
                "pods",
                "-l",
                "type=lapi",
                "-o",
                "jsonpath={.items[0].metadata.name}",
            ],
            check=False,
        )
        if not pod_name:
            return False
        decisions_raw = run_stdout(
            [
                kubectl,
                "--kubeconfig",
                str(session_kubeconfig),
                "-n",
                "crowdsec",
                "exec",
                pod_name,
                "--",
                "cscli",
                "decisions",
                "list",
                "-o",
                "json",
            ],
            check=False,
        )
        try:
            decisions_payload = json.loads(decisions_raw) if decisions_raw else []
        except json.JSONDecodeError:
            return False
        scenarios = crowdsec_operator_probe_ban_scenarios(decisions_payload, source_ip)
        if not scenarios:
            return False
        for scenario in sorted(scenarios):
            run(
                [
                    kubectl,
                    "--kubeconfig",
                    str(session_kubeconfig),
                    "-n",
                    "crowdsec",
                    "exec",
                    pod_name,
                    "--",
                    "cscli",
                    "decisions",
                    "delete",
                    "--ip",
                    source_ip,
                    "--scenario",
                    scenario,
                ],
                check=False,
                capture_output=True,
            )
    return True


def clear_current_operator_crowdsec_probe_ban(
    master_ip: str,
    proxmox_host: str,
    kubeconfig: Path,
    kubectl: str,
) -> bool:
    public_ip = detect_public_ip()
    if public_ip and clear_operator_crowdsec_probe_ban(master_ip, proxmox_host, kubeconfig, kubectl, public_ip):
        return True

    with cluster_session(proxmox_host, master_ip, kubeconfig, kubectl) as session_kubeconfig:
        pod_name = run_stdout(
            [
                kubectl,
                "--kubeconfig",
                str(session_kubeconfig),
                "-n",
                "crowdsec",
                "get",
                "pods",
                "-l",
                "type=lapi",
                "-o",
                "jsonpath={.items[0].metadata.name}",
            ],
            check=False,
        )
        if not pod_name:
            return False
        decisions_raw = run_stdout(
            [
                kubectl,
                "--kubeconfig",
                str(session_kubeconfig),
                "-n",
                "crowdsec",
                "exec",
                pod_name,
                "--",
                "cscli",
                "decisions",
                "list",
                "-o",
                "json",
            ],
            check=False,
        )
        try:
            decisions_payload = json.loads(decisions_raw) if decisions_raw else []
        except json.JSONDecodeError:
            return False
        candidates = crowdsec_operator_probe_ban_ips(decisions_payload)
        if len(candidates) != 1:
            return False
        candidate_ip = next(iter(candidates))
        scenarios = crowdsec_operator_probe_ban_scenarios(decisions_payload, candidate_ip)
        if not scenarios:
            return False
        for scenario in sorted(scenarios):
            run(
                [
                    kubectl,
                    "--kubeconfig",
                    str(session_kubeconfig),
                    "-n",
                    "crowdsec",
                    "exec",
                    pod_name,
                    "--",
                    "cscli",
                    "decisions",
                    "delete",
                    "--ip",
                    candidate_ip,
                    "--scenario",
                    scenario,
                ],
                check=False,
                capture_output=True,
            )
    return True


def restart_traefik_for_crowdsec_recovery(
    master_ip: str,
    proxmox_host: str,
    kubeconfig: Path,
    kubectl: str,
) -> bool:
    try:
        with cluster_session(proxmox_host, master_ip, kubeconfig, kubectl) as session_kubeconfig:
            run(
                [
                    kubectl,
                    "--kubeconfig",
                    str(session_kubeconfig),
                    "-n",
                    "kube-system",
                    "rollout",
                    "restart",
                    "deployment/traefik",
                ],
                capture_output=True,
            )
            run(
                [
                    kubectl,
                    "--kubeconfig",
                    str(session_kubeconfig),
                    "-n",
                    "kube-system",
                    "rollout",
                    "status",
                    "deployment/traefik",
                    "--timeout=180s",
                ],
                capture_output=True,
            )
    except HaaCError:
        return False
    return True


def verify_web(
    domain_name: str,
    retries: int = 30,
    sleep_seconds: int = 10,
    *,
    master_ip: str | None = None,
    proxmox_host: str | None = None,
    kubeconfig: Path | None = None,
    kubectl: str = "kubectl",
    allow_crowdsec_recovery: bool = True,
) -> None:
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
    if (
        failures
        and allow_crowdsec_recovery
        and master_ip
        and proxmox_host
        and kubeconfig is not None
        and all(result["status"] == "403" for result in failures)
    ):
        recovered = False
        if clear_current_operator_crowdsec_probe_ban(master_ip, proxmox_host, kubeconfig, kubectl):
            print("[warn] Cleared temporary CrowdSec false-positive bans for the current operator IP.")
            recovered = True
        if restart_traefik_for_crowdsec_recovery(master_ip, proxmox_host, kubeconfig, kubectl):
            print("[warn] Restarted Traefik to flush the CrowdSec bouncer state after the all-403 failure.")
            recovered = True
        if recovered:
            print("[warn] Retrying public URL verification once after CrowdSec recovery.")
            return verify_web(
                domain_name,
                retries=retries,
                sleep_seconds=sleep_seconds,
                master_ip=master_ip,
                proxmox_host=proxmox_host,
                kubeconfig=kubeconfig,
                kubectl=kubectl,
                allow_crowdsec_recovery=False,
            )
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


def bootstrap_downloaders_session(kubectl: str, session_kubeconfig: Path, env: dict[str, str]) -> None:
    require_env(["QUI_PASSWORD"], env)

    deadline = time.time() + 600
    pod_name = ""
    while time.time() < deadline:
        try:
            pod_name = latest_pod_name(kubectl, session_kubeconfig, "media", "app=downloaders")
        except HaaCError:
            time.sleep(5)
            continue
        if pod_name:
            break
        time.sleep(5)
    else:
        raise HaaCError("Downloader pod did not become available before timeout")

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

    readiness_probe = exec_port_sync(downloaders_readiness_probe_script(), check=False, capture_output=True)
    if readiness_probe.returncode != 0:
        readiness_error = (readiness_probe.stderr or readiness_probe.stdout).strip()
        raise HaaCError(readiness_error or "Downloader APIs did not become ready before timeout.")

    bootstrap_deadline = time.time() + 120
    latest_logs = ""
    while time.time() < bootstrap_deadline:
        latest_logs = run(
            [
                kubectl,
                "--kubeconfig",
                str(session_kubeconfig),
                "logs",
                "-n",
                "media",
                pod_name,
                "-c",
                "port-sync",
                "--tail=120",
            ],
            check=False,
            capture_output=True,
        ).stdout
        if downloaders_bootstrap_succeeded_from_logs(latest_logs):
            config_text = read_downloaders_qbittorrent_config(kubectl, session_kubeconfig, pod_name)
            if not qbittorrent_shared_paths_supported(config_text):
                raise HaaCError(
                    "Downloader bootstrap reached the supported port-sync steady state, "
                    "but qBittorrent still persisted unsupported shared paths.\n"
                    f"{config_text.strip()}"
                )
            return
        time.sleep(5)

    raise HaaCError(
        "Downloader bootstrap did not reach the supported port-sync steady state before timeout.\n"
        + "\n".join(latest_logs.splitlines()[-20:])
    )


def bootstrap_downloaders(master_ip: str, proxmox_host: str, kubeconfig: Path, kubectl: str) -> None:
    env = merged_env()
    with cluster_session(proxmox_host, master_ip, kubeconfig, kubectl) as session_kubeconfig:
        bootstrap_downloaders_session(kubectl, session_kubeconfig, env)


def downloaders_readiness_probe_script() -> str:
    return (
        "wait_http() { "
        "url=\"$1\"; accepted_codes=\"$2\"; attempts=\"$3\"; count=0; "
        "while true; do "
        "code=$(curl --connect-timeout 5 --max-time 20 -sS -o /tmp/wait-http.txt -w '%{http_code}' \"$url\" || true); "
        "if printf '%s\\n' \"$accepted_codes\" | tr ', ' '\\n' | grep -qx \"$code\"; then return 0; fi; "
        "count=$((count + 1)); "
        "if [ \"$attempts\" -gt 0 ] && [ \"$count\" -ge \"$attempts\" ]; then "
        "echo \"Timed out waiting for $url (last HTTP $code)\" >&2; return 1; "
        "fi; "
        "sleep 5; "
        "done; "
        "}; "
        "wait_http 'http://127.0.0.1:7476/api/auth/me' '200' 120; "
        "wait_http 'http://127.0.0.1:8080/api/v2/app/version' '200 403' 120"
    )


def downloaders_bootstrap_succeeded_from_logs(logs: str) -> bool:
    normalized = "\n".join(line.strip().lower() for line in logs.splitlines() if line.strip())
    return (
        "qui instance connectivity test passed." in normalized
        and "qbittorrent category routing reconciled." in normalized
        and "bootstrap complete. starting port-forward sync loop..." in normalized
    )


def normalize_qbittorrent_path(value: str | None) -> str:
    cleaned = str(value or "").strip()
    if not cleaned:
        return ""
    normalized = cleaned.rstrip("/")
    return normalized or "/"


def qbittorrent_config_value(config_text: str, key: str) -> str:
    prefix = f"{key}="
    for raw_line in config_text.splitlines():
        line = raw_line.strip()
        if line.startswith(prefix):
            return line[len(prefix) :].strip()
    return ""


def qbittorrent_shared_paths_supported(config_text: str) -> bool:
    expected_paths = {
        "Session\\DefaultSavePath": QBITTORRENT_SHARED_DOWNLOAD_PATH,
        "Session\\TempPath": QBITTORRENT_SHARED_INCOMPLETE_PATH,
        "Downloads\\SavePath": QBITTORRENT_SHARED_DOWNLOAD_PATH,
        "Downloads\\TempPath": QBITTORRENT_SHARED_INCOMPLETE_PATH,
    }
    for key, expected in expected_paths.items():
        actual = normalize_qbittorrent_path(qbittorrent_config_value(config_text, key))
        if actual != normalize_qbittorrent_path(expected):
            return False
    return True


def qbittorrent_categories_state(
    port: int,
    *,
    opener: urllib.request.OpenerDirector,
) -> dict[str, str]:
    payload = http_request_json(
        f"http://127.0.0.1:{port}/api/v2/torrents/categories",
        opener=opener,
        headers=qbittorrent_webui_headers(),
    )
    if not isinstance(payload, dict):
        return {}
    categories: dict[str, str] = {}
    for name, raw_item in payload.items():
        if not isinstance(raw_item, dict):
            continue
        category_name = str(raw_item.get("name") or name).strip() or str(name).strip()
        if not category_name:
            continue
        categories[category_name] = normalize_qbittorrent_path(raw_item.get("savePath"))
    return categories


def qbittorrent_login(
    port: int,
    *,
    username: str,
    password: str,
) -> urllib.request.OpenerDirector:
    opener = build_cookie_opener()
    status, body = http_request_form_text(
        f"http://127.0.0.1:{port}/api/v2/auth/login",
        fields=(
            ("username", username),
            ("password", password),
        ),
        opener=opener,
    )
    if status != 200 or "ok." not in body.lower():
        raise HaaCError(f"qBittorrent login failed for the managed downloader user.\nHTTP {status}\n{body}")
    return opener


def qbittorrent_webui_headers() -> dict[str, str]:
    return {
        "Host": QBITTORRENT_WEBUI_HOST_HEADER,
        "Referer": f"http://{QBITTORRENT_WEBUI_HOST_HEADER}/",
    }


def qbittorrent_login_via_port_forward(
    port: int,
    *,
    username: str,
    password: str,
) -> urllib.request.OpenerDirector:
    opener = build_cookie_opener()
    status, body = http_request_form_text(
        f"http://127.0.0.1:{port}/api/v2/auth/login",
        fields=(
            ("username", username),
            ("password", password),
        ),
        opener=opener,
        headers=qbittorrent_webui_headers(),
    )
    if status != 200 or "ok." not in body.lower():
        raise HaaCError(f"qBittorrent login failed through the verifier port-forward.\nHTTP {status}\n{body}")
    return opener


def qbittorrent_torrents_info(
    port: int,
    *,
    opener: urllib.request.OpenerDirector,
) -> list[dict[str, object]]:
    return json_array(
        http_request_json(
            f"http://127.0.0.1:{port}/api/v2/torrents/info?filter=all",
            opener=opener,
            headers=qbittorrent_webui_headers(),
        )
    )


def ensure_qbittorrent_category_paths(
    port: int,
    *,
    username: str,
    password: str,
) -> dict[str, str]:
    opener = qbittorrent_login_via_port_forward(port, username=username, password=password)
    current = qbittorrent_categories_state(port, opener=opener)
    for category, save_path in ARR_QBITTORRENT_CATEGORY_SAVE_PATHS.items():
        current_path = current.get(category, "")
        expected_path = normalize_qbittorrent_path(save_path)
        if current_path == expected_path:
            continue
        endpoint = "editCategory" if category in current else "createCategory"
        status, body = http_request_form_text(
            f"http://127.0.0.1:{port}/api/v2/torrents/{endpoint}",
            fields=(
                ("category", category),
                ("savePath", save_path),
            ),
            opener=opener,
            headers=qbittorrent_webui_headers(),
        )
        if status != 200:
            raise HaaCError(f"qBittorrent category bootstrap failed for {category}.\nHTTP {status}\n{body}")
    current = qbittorrent_categories_state(port, opener=opener)
    for category, save_path in ARR_QBITTORRENT_CATEGORY_SAVE_PATHS.items():
        if current.get(category, "") != normalize_qbittorrent_path(save_path):
            raise HaaCError(
                f"qBittorrent category {category} did not persist the supported save path {save_path}."
            )
    return current


def qbittorrent_port_sync_authenticated_script(command: str) -> str:
    return (
        "set -eu; "
        "printenv QBIT_USER >/tmp/qbit-user.txt; "
        "printenv QBIT_PASS >/tmp/qbit-pass.txt; "
        "attempt=0; "
        "while true; do "
        "code=$(curl --connect-timeout 5 --max-time 30 -sS -o /tmp/qbit-version.txt -w '%{http_code}' "
        "http://127.0.0.1:8080/api/v2/app/version || true); "
        "if [ \"$code\" = \"200\" ] || [ \"$code\" = \"403\" ]; then break; fi; "
        "attempt=$((attempt + 1)); "
        "if [ \"$attempt\" -ge 24 ]; then "
        "echo 'qBittorrent WebUI did not become reachable inside the downloader bootstrap container.' >&2; "
        "exit 1; "
        "fi; "
        "sleep 5; "
        "done; "
        "login_body=/tmp/qbit-login.txt; "
        "login_code=$(curl --connect-timeout 5 --max-time 30 -sS -o \"$login_body\" -w '%{http_code}' "
        "-c /tmp/qbit-cookies.txt "
        "--data-urlencode username@/tmp/qbit-user.txt "
        "--data-urlencode password@/tmp/qbit-pass.txt "
        "http://127.0.0.1:8080/api/v2/auth/login || true); "
        "if [ \"$login_code\" != \"200\" ] || ! grep -qi 'Ok\\.' \"$login_body\"; then "
        "echo 'qBittorrent login failed inside the downloader bootstrap container.' >&2; "
        "cat \"$login_body\" >&2; "
        "exit 1; "
        "fi; "
        + command
    )


def qbittorrent_categories_state_in_session(
    kubectl: str,
    kubeconfig: Path,
    *,
    pod_name: str,
) -> dict[str, str]:
    body = kubectl_exec_stdout(
        kubectl,
        kubeconfig,
        namespace="media",
        pod=pod_name,
        container="port-sync",
        script=qbittorrent_port_sync_authenticated_script(
            "curl --connect-timeout 5 --max-time 30 -fsS -b /tmp/qbit-cookies.txt "
            "http://127.0.0.1:8080/api/v2/torrents/categories"
        ),
    )
    try:
        payload = json.loads(body)
    except json.JSONDecodeError as exc:
        raise HaaCError("qBittorrent categories API returned invalid JSON.") from exc
    if not isinstance(payload, dict):
        return {}
    categories: dict[str, str] = {}
    for name, raw_item in payload.items():
        if not isinstance(raw_item, dict):
            continue
        category_name = str(raw_item.get("name") or name).strip() or str(name).strip()
        if not category_name:
            continue
        categories[category_name] = normalize_qbittorrent_path(raw_item.get("savePath"))
    return categories


def ensure_qbittorrent_category_paths_in_session(
    kubectl: str,
    kubeconfig: Path,
    *,
    pod_name: str,
) -> dict[str, str]:
    current = qbittorrent_categories_state_in_session(kubectl, kubeconfig, pod_name=pod_name)
    for category, save_path in ARR_QBITTORRENT_CATEGORY_SAVE_PATHS.items():
        current_path = current.get(category, "")
        expected_path = normalize_qbittorrent_path(save_path)
        if current_path == expected_path:
            continue
        endpoint = "editCategory" if category in current else "createCategory"
        kubectl_exec_stdout(
            kubectl,
            kubeconfig,
            namespace="media",
            pod=pod_name,
            container="port-sync",
            script=qbittorrent_port_sync_authenticated_script(
                "curl --connect-timeout 5 --max-time 30 -fsS -b /tmp/qbit-cookies.txt "
                f"--data-urlencode {shlex.quote(f'category={category}')} "
                f"--data-urlencode {shlex.quote(f'savePath={save_path}')} "
                f"http://127.0.0.1:8080/api/v2/torrents/{endpoint} >/dev/null"
            ),
        )
    current = qbittorrent_categories_state_in_session(kubectl, kubeconfig, pod_name=pod_name)
    for category, save_path in ARR_QBITTORRENT_CATEGORY_SAVE_PATHS.items():
        if current.get(category, "") != normalize_qbittorrent_path(save_path):
            raise HaaCError(
                f"qBittorrent category {category} did not persist the supported save path {save_path}."
            )
    return current


def read_downloaders_qbittorrent_config(kubectl: str, kubeconfig: Path, pod_name: str) -> str:
    return run_stdout(
        [
            kubectl,
            "--kubeconfig",
            str(kubeconfig),
            "exec",
            "-n",
            "media",
            pod_name,
            "-c",
            "qbittorrent",
            "--",
            "/bin/sh",
            "-ec",
            "cat /config/qBittorrent/qBittorrent.conf",
        ]
    )


def detect_vpn_blocker_from_logs(logs: str) -> str:
    lines = [line.strip() for line in logs.splitlines() if line.strip()]
    if not lines:
        return ""
    normalized = "\n".join(line.lower() for line in lines)
    if "initialization sequence completed" in normalized and "port forwarded is" in normalized:
        return ""
    blocker_markers = (
        "auth failed",
        "auth_failed",
        "cannot authenticate",
        "your credentials might be wrong",
        "subscription",
        "plan doesn't support",
        "plan does not support",
        "make sure you have +pmp",
        "port forwarding failed",
        "failed to get port forwarded",
        "failed to start the vpn",
    )
    matching = [line for line in lines if any(marker in line.lower() for marker in blocker_markers)]
    if not matching:
        return ""
    return "\n".join(matching[-5:])


def detect_vpn_blocker(kubectl: str, kubeconfig: Path) -> str:
    try:
        pod_name = latest_pod_name(kubectl, kubeconfig, "media", "app=downloaders")
    except HaaCError:
        return ""
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
            "gluetun",
            "--tail=120",
        ],
        check=False,
        capture_output=True,
    ).stdout
    return detect_vpn_blocker_from_logs(logs)


def read_arr_service_api_key(kubectl: str, kubeconfig: Path, app_name: str) -> str:
    pod_name = latest_pod_name(kubectl, kubeconfig, "media", f"app={app_name}")
    config_xml = kubectl_exec_stdout(
        kubectl,
        kubeconfig,
        namespace="media",
        pod=pod_name,
        container=app_name,
        script="cat /config/config.xml",
    )
    try:
        root = ET.fromstring(config_xml)
    except ET.ParseError as exc:
        raise HaaCError(f"{app_name} config.xml is not valid XML") from exc
    api_key = xml_element_text(root, "ApiKey")
    if not api_key:
        raise HaaCError(f"{app_name} config.xml does not contain an ApiKey")
    return api_key


def parse_sabnzbd_service_api_key(config_text: str) -> str:
    normalized = config_text.lstrip("\ufeff")
    first_section = normalized.find("[")
    if first_section >= 0:
        normalized = normalized[first_section:]
    parser = configparser.ConfigParser(interpolation=None)
    try:
        parser.read_string(normalized)
    except configparser.Error:
        parser = None
    else:
        api_key = parser.get("misc", "api_key", fallback="").strip()
        if api_key:
            return api_key

    misc_match = re.search(r"(?ms)^\[misc\]\s*(.*?)(?=^\[|\Z)", normalized)
    if misc_match:
        api_key_match = re.search(r"(?m)^\s*api_key\s*=\s*(.+?)\s*$", misc_match.group(1))
        if api_key_match:
            api_key = api_key_match.group(1).strip()
            if api_key:
                return api_key
    raise HaaCError("SABnzbd config does not expose an api_key yet.")


def read_sabnzbd_service_api_key(kubectl: str, kubeconfig: Path) -> str:
    pod_name = latest_pod_name(kubectl, kubeconfig, "media", "app=sabnzbd")
    script = r"""
set -eu
if [ -f /config/sabnzbd.ini ]; then
  cat /config/sabnzbd.ini
  exit 0
fi
config_path="$(find /config -name sabnzbd.ini -print -quit 2>/dev/null || true)"
if [ -n "$config_path" ] && [ -f "$config_path" ]; then
  cat "$config_path"
  exit 0
fi
echo "SABnzbd sabnzbd.ini not found under /config" >&2
exit 1
"""
    config_text = kubectl_exec_stdout(
        kubectl,
        kubeconfig,
        namespace="media",
        pod=pod_name,
        container="sabnzbd",
        script=script,
    )
    return parse_sabnzbd_service_api_key(config_text)


def require_http_status(
    url: str,
    *,
    label: str,
    expected_statuses: tuple[int, ...] = (200,),
    expected_body_pattern: str | None = None,
    opener: urllib.request.OpenerDirector | None = None,
) -> str:
    status, body = http_request_text(url, opener=opener)
    if status not in expected_statuses:
        raise HaaCError(f"{label} returned HTTP {status} instead of {expected_statuses}: {body}")
    if expected_body_pattern and not re.search(expected_body_pattern, body, flags=re.IGNORECASE):
        raise HaaCError(f"{label} did not render the expected body pattern {expected_body_pattern!r}")
    return body


def preferred_option(
    items: list[dict[str, object]],
    *,
    name_preferences: tuple[str, ...] = (),
    path_preferences: tuple[str, ...] = (),
) -> dict[str, object]:
    if not items:
        raise HaaCError("The expected option list is empty.")
    if name_preferences:
        for preferred in name_preferences:
            for item in items:
                if str(item.get("name") or "").strip().lower() == preferred.lower():
                    return item
    if path_preferences:
        for preferred in path_preferences:
            for item in items:
                if str(item.get("path") or "").strip() == preferred:
                    return item
    return items[0]


def ensure_arr_root_folder(
    port: int,
    *,
    app_name: str,
    api_key: str,
    path: str,
    api_version: str = "v3",
) -> list[dict[str, object]]:
    headers = {"X-Api-Key": api_key}
    base_url = f"http://127.0.0.1:{port}/api/{api_version}/rootfolder"
    current = json_array(http_request_json(base_url, headers=headers))
    if any(str(item.get("path") or "").strip() == path for item in current):
        return current
    payload: dict[str, object] = {"path": path}
    if app_name.strip().lower() == "lidarr" and api_version == "v1":
        quality_profiles = json_array(http_request_json(f"http://127.0.0.1:{port}/api/{api_version}/qualityprofile", headers=headers))
        metadata_profiles = json_array(http_request_json(f"http://127.0.0.1:{port}/api/{api_version}/metadataprofile", headers=headers))
        default_quality_profile_id = next((int(item.get("id") or 0) for item in quality_profiles if int(item.get("id") or 0) > 0), 0)
        default_metadata_profile_id = next((int(item.get("id") or 0) for item in metadata_profiles if int(item.get("id") or 0) > 0), 0)
        if default_quality_profile_id <= 0:
            raise HaaCError("Lidarr root-folder bootstrap could not resolve a usable quality profile.")
        if default_metadata_profile_id <= 0:
            raise HaaCError("Lidarr root-folder bootstrap could not resolve a usable metadata profile.")
        folder_name = PurePosixPath(path).name.replace("-", " ").strip().title() or "Music"
        payload = {
            "name": folder_name,
            "path": path,
            "defaultQualityProfileId": default_quality_profile_id,
            "defaultMetadataProfileId": default_metadata_profile_id,
            "defaultTags": [],
        }
    status, body = http_request_text(
        base_url,
        method="POST",
        payload=payload,
        headers=headers,
    )
    if status not in (200, 201):
        raise HaaCError(f"{app_name} root-folder bootstrap failed for {path}.\nHTTP {status}\n{body}")
    current = json_array(http_request_json(base_url, headers=headers))
    if not any(str(item.get("path") or "").strip() == path for item in current):
        raise HaaCError(f"{app_name} root-folder bootstrap did not persist {path}.")
    return current


def qbittorrent_preferences_state(
    port: int,
    *,
    opener: urllib.request.OpenerDirector,
) -> dict[str, object]:
    return json_object(
        http_request_json(
            f"http://127.0.0.1:{port}/api/v2/app/preferences",
            opener=opener,
            headers=qbittorrent_webui_headers(),
        )
    )


def ensure_qbittorrent_app_preferences(
    port: int,
    *,
    username: str,
    password: str,
) -> dict[str, object]:
    opener = qbittorrent_login_via_port_forward(port, username=username, password=password)
    current = qbittorrent_preferences_state(port, opener=opener)
    desired = {
        key: value
        for key, value in QBITTORRENT_APP_PREFERENCE_DEFAULTS.items()
        if current.get(key) != value
    }
    if desired:
        status, body = http_request_form_text(
            f"http://127.0.0.1:{port}/api/v2/app/setPreferences",
            fields=(("json", json.dumps(desired, separators=(",", ":"))),),
            opener=opener,
            headers=qbittorrent_webui_headers(),
        )
        if status != 200:
            raise HaaCError(f"qBittorrent preference bootstrap failed.\nHTTP {status}\n{body}")
    current = qbittorrent_preferences_state(port, opener=opener)
    for key, value in QBITTORRENT_APP_PREFERENCE_DEFAULTS.items():
        if current.get(key) != value:
            raise HaaCError(f"qBittorrent preference {key} did not persist the supported value {value!r}.")
    return current


def arr_config_url(port: int, *, api_version: str, config_name: str) -> str:
    return f"http://127.0.0.1:{port}/api/{api_version}/config/{config_name}"


def arr_config_json(
    port: int,
    *,
    api_key: str,
    config_name: str,
    api_version: str = "v3",
) -> dict[str, object]:
    data = http_request_json(arr_config_url(port, api_version=api_version, config_name=config_name), headers={"X-Api-Key": api_key})
    if not isinstance(data, dict):
        raise HaaCError(f"ARR config endpoint {config_name!r} returned an unexpected response.")
    return data


def ensure_arr_config_fragment(
    port: int,
    *,
    app_name: str,
    api_key: str,
    config_name: str,
    desired: dict[str, object],
    api_version: str = "v3",
) -> dict[str, object]:
    current = arr_config_json(port, api_key=api_key, config_name=config_name, api_version=api_version)
    if all(current.get(key) == value for key, value in desired.items()):
        return current
    payload = copy.deepcopy(current)
    payload.update(desired)
    status, body = http_request_text(
        arr_config_url(port, api_version=api_version, config_name=config_name),
        method="PUT",
        payload=payload,
        headers={"X-Api-Key": api_key},
    )
    if status not in (200, 202):
        raise HaaCError(f"{app_name} {config_name} bootstrap failed.\nHTTP {status}\n{body}")
    refreshed = arr_config_json(port, api_key=api_key, config_name=config_name, api_version=api_version)
    for key, value in desired.items():
        if refreshed.get(key) != value:
            raise HaaCError(f"{app_name} {config_name} bootstrap did not persist {key}={value!r}.")
    return refreshed


def ensure_arr_common_settings(
    port: int,
    *,
    app_name: str,
    api_key: str,
    api_version: str = "v3",
) -> None:
    app_key = app_name.strip().lower()
    if app_key not in ARR_COMMON_NAMING_DEFAULTS:
        raise HaaCError(f"Unsupported ARR common-settings target: {app_name}")
    ensure_arr_config_fragment(
        port,
        app_name=app_name,
        api_key=api_key,
        config_name="naming",
        desired=ARR_COMMON_NAMING_DEFAULTS[app_key],
        api_version=api_version,
    )
    ensure_arr_config_fragment(
        port,
        app_name=app_name,
        api_key=api_key,
        config_name="mediamanagement",
        desired=ARR_COMMON_MEDIA_MANAGEMENT_DEFAULTS,
        api_version=api_version,
    )
    ensure_arr_config_fragment(
        port,
        app_name=app_name,
        api_key=api_key,
        config_name="downloadclient",
        desired=ARR_COMMON_DOWNLOAD_CLIENT_DEFAULTS,
        api_version=api_version,
    )


def schema_item_by_implementation(
    schema_items: list[dict[str, object]],
    *,
    implementation: str,
    label: str,
) -> dict[str, object]:
    for item in schema_items:
        if str(item.get("implementation") or "").strip().lower() == implementation.lower():
            return copy.deepcopy(item)
    raise HaaCError(f"{label} schema does not expose implementation {implementation}.")


def field_value(fields: list[dict[str, object]], name: str) -> object:
    for field in fields:
        if str(field.get("name") or "").strip() == name:
            return field.get("value")
    return None


def set_field_value(fields: list[dict[str, object]], name: str, value: object, *, required: bool = True) -> None:
    for field in fields:
        if str(field.get("name") or "").strip() == name:
            field["value"] = value
            return
    if required:
        raise HaaCError(f"Schema field {name!r} is missing from the requested payload.")


def find_service_integration(
    items: list[dict[str, object]],
    *,
    implementation: str,
    name: str | None = None,
) -> dict[str, object] | None:
    exact_name = None
    fallback = None
    for item in items:
        if str(item.get("implementation") or "").strip().lower() != implementation.lower():
            continue
        if fallback is None:
            fallback = copy.deepcopy(item)
        if name and str(item.get("name") or "").strip() == name:
            exact_name = copy.deepcopy(item)
            break
    return exact_name or fallback


def set_first_field_value(fields: list[dict[str, object]], names: tuple[str, ...], value: object) -> str | None:
    for name in names:
        for field in fields:
            if str(field.get("name") or "").strip() == name:
                field["value"] = value
                return name
    return None


def find_named_item(items: list[dict[str, object]], *, name: str) -> dict[str, object] | None:
    target = name.strip().lower()
    for item in items:
        if str(item.get("name") or "").strip().lower() == target:
            return copy.deepcopy(item)
    return None


def canonical_arr_language_preferences(raw: str | None) -> tuple[str, ...]:
    value = str(raw or "").strip()
    if not value:
        return ARR_LANGUAGE_PREFERENCE_DEFAULT
    canonical: list[str] = []
    for token in value.split(","):
        normalized = token.strip().lower()
        if not normalized:
            continue
        language = ARR_LANGUAGE_CODE_ALIASES.get(normalized)
        if not language:
            raise HaaCError(
                "ARR_PREFERRED_AUDIO_LANGUAGES contains an unsupported value. "
                "Use comma-separated ISO codes or names such as `it,en`."
            )
        if language not in canonical:
            canonical.append(language)
    if not canonical:
        return ARR_LANGUAGE_PREFERENCE_DEFAULT
    return tuple(canonical)


def desired_arr_language_preferences(env: dict[str, str]) -> tuple[str, ...]:
    return canonical_arr_language_preferences(env.get("ARR_PREFERRED_AUDIO_LANGUAGES"))


def arr_language_preference_scores(preferences: tuple[str, ...]) -> dict[str, int]:
    scores: dict[str, int] = {}
    fallback_score = 25
    for index, language in enumerate(preferences):
        scores[language] = ARR_LANGUAGE_SCORE_OVERRIDES.get(language, max(10, fallback_score - (index * 5)))
    return scores


def arr_language_custom_format_name(language_name: str) -> str:
    return f"{ARR_LANGUAGE_CUSTOM_FORMAT_PREFIX}{language_name}"


def arr_language_schema_item(
    port: int,
    *,
    app_name: str,
    api_key: str,
    api_version: str = "v3",
) -> dict[str, object]:
    schema = json_array(http_request_json(f"http://127.0.0.1:{port}/api/{api_version}/customformat/schema", headers={"X-Api-Key": api_key}))
    return schema_item_by_implementation(schema, implementation="LanguageSpecification", label=f"{app_name} language custom format")


def arr_language_option_value(language_schema: dict[str, object], language_name: str) -> int:
    fields = json_array(language_schema.get("fields"))
    for field in fields:
        if str(field.get("name") or "").strip() != "value":
            continue
        for option in json_array(field.get("selectOptions")):
            if str(option.get("name") or "").strip().lower() == language_name.strip().lower():
                return int(option.get("value") or 0)
    raise HaaCError(f"Language {language_name!r} is not supported by the current ARR custom-format schema.")


def build_arr_language_custom_format(
    language_schema: dict[str, object],
    *,
    format_name: str,
    language_value: int,
) -> dict[str, object]:
    specification = copy.deepcopy(language_schema)
    specification["name"] = f"{format_name} matcher"
    fields = json_array(specification.get("fields"))
    set_field_value(fields, "value", language_value)
    set_field_value(fields, "exceptLanguage", False, required=False)
    specification["fields"] = fields
    return {
        "name": format_name,
        "includeCustomFormatWhenRenaming": False,
        "specifications": [specification],
    }


def ensure_arr_language_custom_format(
    port: int,
    *,
    app_name: str,
    api_key: str,
    format_name: str,
    language_name: str,
    api_version: str = "v3",
) -> dict[str, object]:
    headers = {"X-Api-Key": api_key}
    base_url = f"http://127.0.0.1:{port}/api/{api_version}/customformat"
    language_schema = arr_language_schema_item(port, app_name=app_name, api_key=api_key, api_version=api_version)
    language_value = arr_language_option_value(language_schema, language_name)
    desired = build_arr_language_custom_format(language_schema, format_name=format_name, language_value=language_value)
    current = json_array(http_request_json(base_url, headers=headers))
    existing = find_named_item(current, name=format_name)
    if existing:
        payload = copy.deepcopy(existing)
        payload["includeCustomFormatWhenRenaming"] = False
        payload["specifications"] = desired["specifications"]
        http_request_json(f"{base_url}/{payload['id']}", method="PUT", payload=payload, headers=headers)
    else:
        http_request_json(base_url, method="POST", payload=desired, headers=headers)
    refreshed = json_array(http_request_json(base_url, headers=headers))
    persisted = find_named_item(refreshed, name=format_name)
    if not persisted:
        raise HaaCError(f"{app_name} custom format {format_name!r} did not persist.")
    specifications = json_array(persisted.get("specifications"))
    if not specifications:
        raise HaaCError(f"{app_name} custom format {format_name!r} persisted without specifications.")
    fields = json_array(specifications[0].get("fields"))
    if int(field_value(fields, "value") or 0) != language_value:
        raise HaaCError(f"{app_name} custom format {format_name!r} persisted with an unexpected language value.")
    return persisted


def ensure_arr_language_preferences(
    port: int,
    *,
    app_name: str,
    api_key: str,
    preferred_languages: tuple[str, ...],
    api_version: str = "v3",
) -> None:
    headers = {"X-Api-Key": api_key}
    desired_formats: list[dict[str, object]] = []
    for language_name, score in arr_language_preference_scores(preferred_languages).items():
        format_name = arr_language_custom_format_name(language_name)
        persisted = ensure_arr_language_custom_format(
            port,
            app_name=app_name,
            api_key=api_key,
            format_name=format_name,
            language_name=language_name,
            api_version=api_version,
        )
        desired_formats.append({"id": int(persisted.get("id") or 0), "name": format_name, "score": score})

    base_url = f"http://127.0.0.1:{port}/api/{api_version}/qualityprofile"
    quality_profiles = json_array(http_request_json(base_url, headers=headers))
    for profile in quality_profiles:
        profile_name = str(profile.get("name") or "").strip()
        if not profile_name:
            continue
        format_items = json_array(profile.get("formatItems"))
        changed = False
        for desired in desired_formats:
            existing_item = next(
                (
                    item
                    for item in format_items
                    if int(item.get("format") or 0) == desired["id"]
                    or str(item.get("name") or "").strip() == desired["name"]
                ),
                None,
            )
            if existing_item is None:
                format_items.append({"format": desired["id"], "name": desired["name"], "score": desired["score"]})
                changed = True
                continue
            if int(existing_item.get("format") or 0) != desired["id"]:
                existing_item["format"] = desired["id"]
                changed = True
            if str(existing_item.get("name") or "").strip() != desired["name"]:
                existing_item["name"] = desired["name"]
                changed = True
            if int(existing_item.get("score") or 0) != desired["score"]:
                existing_item["score"] = desired["score"]
                changed = True
        if not changed:
            continue
        profile["formatItems"] = format_items
        http_request_json(f"{base_url}/{profile['id']}", method="PUT", payload=profile, headers=headers)

    refreshed_profiles = json_array(http_request_json(base_url, headers=headers))
    for profile in refreshed_profiles:
        profile_name = str(profile.get("name") or "").strip()
        if not profile_name:
            continue
        format_items = json_array(profile.get("formatItems"))
        for desired in desired_formats:
            persisted = next(
                (
                    item
                    for item in format_items
                    if int(item.get("format") or 0) == desired["id"]
                    and str(item.get("name") or "").strip() == desired["name"]
                ),
                None,
            )
            if persisted is None or int(persisted.get("score") or 0) != desired["score"]:
                raise HaaCError(
                    f"{app_name} quality profile {profile_name!r} did not persist the language preference "
                    f"{desired['name']!r} with score {desired['score']}."
                )


def ensure_arr_qbittorrent_download_client(
    port: int,
    *,
    app_name: str,
    api_key: str,
    username: str,
    password: str,
    api_version: str = "v3",
) -> list[dict[str, object]]:
    app_key = app_name.strip().lower()
    if app_key not in ("radarr", "sonarr", "lidarr", "whisparr"):
        raise HaaCError(f"Unsupported ARR qBittorrent target: {app_name}")
    headers = {"X-Api-Key": api_key}
    base_url = f"http://127.0.0.1:{port}/api/{api_version}/downloadclient"
    current = json_array(http_request_json(base_url, headers=headers))
    existing = find_service_integration(current, implementation="QBittorrent", name=ARR_QBITTORRENT_CLIENT_NAME)
    if existing:
        payload = existing
    else:
        schema = json_array(http_request_json(f"{base_url}/schema", headers=headers))
        payload = schema_item_by_implementation(
            schema,
            implementation="QBittorrent",
            label=f"{app_name} download client",
        )
    fields = json_array(payload.get("fields"))
    payload["enable"] = True
    payload["name"] = ARR_QBITTORRENT_CLIENT_NAME
    set_field_value(fields, "host", QBITTORRENT_INTERNAL_HOST)
    set_field_value(fields, "port", QBITTORRENT_INTERNAL_PORT)
    set_field_value(fields, "useSsl", False, required=False)
    set_field_value(fields, "urlBase", "", required=False)
    set_field_value(fields, "username", username)
    set_field_value(fields, "password", password)
    if app_key in ("radarr", "whisparr"):
        set_field_value(fields, "movieCategory", ARR_QBITTORRENT_CATEGORIES[app_key])
        set_field_value(
            fields,
            "movieImportedCategory",
            ARR_QBITTORRENT_IMPORTED_CATEGORIES[app_key],
            required=False,
        )
    elif app_key == "sonarr":
        set_field_value(fields, "tvCategory", ARR_QBITTORRENT_CATEGORIES["sonarr"])
        set_field_value(
            fields,
            "tvImportedCategory",
            ARR_QBITTORRENT_IMPORTED_CATEGORIES["sonarr"],
            required=False,
        )
    else:
        if not set_first_field_value(fields, ("category", "musicCategory"), ARR_QBITTORRENT_CATEGORIES["lidarr"]):
            raise HaaCError("Lidarr qBittorrent schema does not expose a supported category field.")
        set_first_field_value(
            fields,
            ("postImportCategory", "importedCategory", "postImportCompletedCategory"),
            ARR_QBITTORRENT_IMPORTED_CATEGORIES["lidarr"],
        )
    payload["fields"] = fields
    test_status, test_body = http_request_text(
        f"{base_url}/test",
        method="POST",
        payload=payload,
        headers=headers,
    )
    if test_status not in (200, 204):
        raise HaaCError(f"{app_name} qBittorrent test failed.\nHTTP {test_status}\n{test_body}")
    if existing and payload.get("id"):
        status, body = http_request_text(
            f"{base_url}/{payload['id']}",
            method="PUT",
            payload=payload,
            headers=headers,
        )
        expected = (200, 202)
    else:
        status, body = http_request_text(base_url, method="POST", payload=payload, headers=headers)
        expected = (200, 201, 202)
    if status not in expected:
        raise HaaCError(f"{app_name} qBittorrent bootstrap failed.\nHTTP {status}\n{body}")
    current = json_array(http_request_json(base_url, headers=headers))
    configured = find_service_integration(current, implementation="QBittorrent", name=ARR_QBITTORRENT_CLIENT_NAME)
    if not configured:
        raise HaaCError(f"{app_name} qBittorrent client did not persist.")
    configured_fields = json_array(configured.get("fields"))
    if str(field_value(configured_fields, "host") or "").strip() != QBITTORRENT_INTERNAL_HOST:
        raise HaaCError(f"{app_name} qBittorrent client persisted with an unexpected host.")
    return current


def ensure_arr_sabnzbd_download_client(
    port: int,
    *,
    app_name: str,
    api_key: str,
    sabnzbd_api_key: str,
    api_version: str = "v3",
) -> list[dict[str, object]]:
    app_key = app_name.strip().lower()
    if app_key not in ("radarr", "sonarr", "lidarr", "whisparr"):
        raise HaaCError(f"Unsupported ARR SABnzbd target: {app_name}")
    headers = {"X-Api-Key": api_key}
    base_url = f"http://127.0.0.1:{port}/api/{api_version}/downloadclient"
    current = json_array(http_request_json(base_url, headers=headers))
    existing = find_service_integration(current, implementation="Sabnzbd", name=ARR_SABNZBD_CLIENT_NAME)
    if existing:
        payload = existing
    else:
        schema = json_array(http_request_json(f"{base_url}/schema", headers=headers))
        payload = schema_item_by_implementation(
            schema,
            implementation="Sabnzbd",
            label=f"{app_name} download client",
        )
    fields = json_array(payload.get("fields"))
    payload["enable"] = True
    payload["name"] = ARR_SABNZBD_CLIENT_NAME
    set_field_value(fields, "host", SABNZBD_INTERNAL_HOST)
    set_field_value(fields, "port", SABNZBD_INTERNAL_PORT)
    set_field_value(fields, "useSsl", False, required=False)
    set_field_value(fields, "urlBase", "", required=False)
    set_field_value(fields, "apiKey", sabnzbd_api_key)
    set_field_value(fields, "username", "", required=False)
    set_field_value(fields, "password", "", required=False)
    category_name = ARR_SABNZBD_CATEGORIES[app_key]
    if app_key in ("radarr", "whisparr"):
        if not set_first_field_value(fields, ("movieCategory", "category"), category_name):
            raise HaaCError(f"{app_name} SABnzbd schema does not expose a supported category field.")
    elif app_key == "sonarr":
        if not set_first_field_value(fields, ("tvCategory", "category"), category_name):
            raise HaaCError("Sonarr SABnzbd schema does not expose a supported category field.")
    else:
        if not set_first_field_value(fields, ("musicCategory", "category"), category_name):
            raise HaaCError("Lidarr SABnzbd schema does not expose a supported category field.")
    set_first_field_value(fields, ("recentTvPriority", "olderTvPriority", "priority"), -100)
    payload["fields"] = fields
    test_status, test_body = http_request_text(
        f"{base_url}/test",
        method="POST",
        payload=payload,
        headers=headers,
    )
    if test_status not in (200, 204):
        raise HaaCError(f"{app_name} SABnzbd test failed.\nHTTP {test_status}\n{test_body}")
    if existing and payload.get("id"):
        status, body = http_request_text(
            f"{base_url}/{payload['id']}",
            method="PUT",
            payload=payload,
            headers=headers,
        )
        expected = (200, 202)
    else:
        status, body = http_request_text(base_url, method="POST", payload=payload, headers=headers)
        expected = (200, 201, 202)
    if status not in expected:
        raise HaaCError(f"{app_name} SABnzbd bootstrap failed.\nHTTP {status}\n{body}")
    current = json_array(http_request_json(base_url, headers=headers))
    configured = find_service_integration(current, implementation="Sabnzbd", name=ARR_SABNZBD_CLIENT_NAME)
    if not configured:
        raise HaaCError(f"{app_name} SABnzbd client did not persist.")
    configured_fields = json_array(configured.get("fields"))
    if str(field_value(configured_fields, "host") or "").strip() != SABNZBD_INTERNAL_HOST:
        raise HaaCError(f"{app_name} SABnzbd client persisted with an unexpected host.")
    return current


def ensure_prowlarr_qbittorrent_download_client(
    port: int,
    *,
    api_key: str,
    username: str,
    password: str,
) -> list[dict[str, object]]:
    headers = {"X-Api-Key": api_key}
    base_url = f"http://127.0.0.1:{port}/api/v1/downloadclient"
    current = json_array(http_request_json(base_url, headers=headers))
    existing = find_service_integration(current, implementation="QBittorrent", name=ARR_QBITTORRENT_CLIENT_NAME)
    if existing:
        payload = existing
    else:
        schema = json_array(http_request_json(f"{base_url}/schema", headers=headers))
        payload = schema_item_by_implementation(
            schema,
            implementation="QBittorrent",
            label="Prowlarr download client",
        )
    fields = json_array(payload.get("fields"))
    payload["enable"] = True
    payload["name"] = ARR_QBITTORRENT_CLIENT_NAME
    set_field_value(fields, "host", QBITTORRENT_INTERNAL_HOST)
    set_field_value(fields, "port", QBITTORRENT_INTERNAL_PORT)
    set_field_value(fields, "useSsl", False, required=False)
    set_field_value(fields, "urlBase", "", required=False)
    set_field_value(fields, "username", username)
    set_field_value(fields, "password", password)
    set_field_value(fields, "category", ARR_QBITTORRENT_CATEGORIES["prowlarr"])
    payload["fields"] = fields
    if existing and payload.get("id"):
        status, body = http_request_text(
            f"{base_url}/{payload['id']}",
            method="PUT",
            payload=payload,
            headers=headers,
        )
        expected = (200, 202)
    else:
        status, body = http_request_text(base_url, method="POST", payload=payload, headers=headers)
        expected = (200, 201, 202)
    if status not in expected:
        raise HaaCError(f"Prowlarr qBittorrent bootstrap failed.\nHTTP {status}\n{body}")
    current = json_array(http_request_json(base_url, headers=headers))
    configured = find_service_integration(current, implementation="QBittorrent", name=ARR_QBITTORRENT_CLIENT_NAME)
    if not configured:
        raise HaaCError("Prowlarr qBittorrent client did not persist.")
    configured_fields = json_array(configured.get("fields"))
    if str(field_value(configured_fields, "host") or "").strip() != QBITTORRENT_INTERNAL_HOST:
        raise HaaCError("Prowlarr qBittorrent client persisted with an unexpected host.")
    return current


def ensure_prowlarr_sabnzbd_download_client(
    port: int,
    *,
    api_key: str,
    sabnzbd_api_key: str,
) -> list[dict[str, object]]:
    headers = {"X-Api-Key": api_key}
    base_url = f"http://127.0.0.1:{port}/api/v1/downloadclient"
    current = json_array(http_request_json(base_url, headers=headers))
    existing = find_service_integration(current, implementation="Sabnzbd", name=ARR_SABNZBD_CLIENT_NAME)
    if existing:
        payload = existing
    else:
        schema = json_array(http_request_json(f"{base_url}/schema", headers=headers))
        payload = schema_item_by_implementation(
            schema,
            implementation="Sabnzbd",
            label="Prowlarr download client",
        )
    fields = json_array(payload.get("fields"))
    payload["enable"] = True
    payload["name"] = ARR_SABNZBD_CLIENT_NAME
    set_field_value(fields, "host", SABNZBD_INTERNAL_HOST)
    set_field_value(fields, "port", SABNZBD_INTERNAL_PORT)
    set_field_value(fields, "useSsl", False, required=False)
    set_field_value(fields, "urlBase", "", required=False)
    set_field_value(fields, "apiKey", sabnzbd_api_key)
    set_field_value(fields, "username", "", required=False)
    set_field_value(fields, "password", "", required=False)
    if not set_first_field_value(fields, ("category",), ARR_SABNZBD_CATEGORIES["prowlarr"]):
        raise HaaCError("Prowlarr SABnzbd schema does not expose a supported category field.")
    payload["fields"] = fields
    if existing and payload.get("id"):
        status, body = http_request_text(
            f"{base_url}/{payload['id']}",
            method="PUT",
            payload=payload,
            headers=headers,
        )
        expected = (200, 202)
    else:
        status, body = http_request_text(base_url, method="POST", payload=payload, headers=headers)
        expected = (200, 201, 202)
    if status not in expected:
        raise HaaCError(f"Prowlarr SABnzbd bootstrap failed.\nHTTP {status}\n{body}")
    current = json_array(http_request_json(base_url, headers=headers))
    configured = find_service_integration(current, implementation="Sabnzbd", name=ARR_SABNZBD_CLIENT_NAME)
    if not configured:
        raise HaaCError("Prowlarr SABnzbd client did not persist.")
    return current


def ensure_prowlarr_application(
    port: int,
    *,
    api_key: str,
    implementation: str,
    downstream_api_key: str,
    downstream_url: str,
) -> list[dict[str, object]]:
    headers = {"X-Api-Key": api_key}
    base_url = f"http://127.0.0.1:{port}/api/v1/applications"
    current = json_array(http_request_json(base_url, headers=headers))
    existing = find_service_integration(current, implementation=implementation, name=implementation)
    if existing:
        payload = existing
    else:
        schema = json_array(http_request_json(f"{base_url}/schema", headers=headers))
        payload = schema_item_by_implementation(
            schema,
            implementation=implementation,
            label="Prowlarr application",
        )
    fields = json_array(payload.get("fields"))
    payload["enable"] = True
    payload["name"] = implementation
    payload["syncLevel"] = str(payload.get("syncLevel") or "fullSync")
    set_field_value(fields, "prowlarrUrl", PROWLARR_INTERNAL_URL)
    set_field_value(fields, "baseUrl", downstream_url)
    set_field_value(fields, "apiKey", downstream_api_key)
    payload["fields"] = fields
    if existing and payload.get("id"):
        status, body = http_request_text(
            f"{base_url}/{payload['id']}",
            method="PUT",
            payload=payload,
            headers=headers,
        )
        expected = (200, 202)
    else:
        status, body = http_request_text(base_url, method="POST", payload=payload, headers=headers)
        expected = (200, 201, 202)
    if status not in expected:
        raise HaaCError(f"Prowlarr {implementation} bootstrap failed.\nHTTP {status}\n{body}")
    current = json_array(http_request_json(base_url, headers=headers))
    configured = find_service_integration(current, implementation=implementation, name=implementation)
    if not configured:
        raise HaaCError(f"Prowlarr {implementation} application did not persist.")
    configured_fields = json_array(configured.get("fields"))
    if str(field_value(configured_fields, "baseUrl") or "").strip() != downstream_url:
        raise HaaCError(f"Prowlarr {implementation} application persisted with an unexpected URL.")
    return current


def sabnzbd_api_request_json(
    port: int,
    *,
    api_key: str | None = None,
    timeout: int = 60,
    **params: object,
) -> dict[str, object]:
    query_params: dict[str, object] = {"output": "json", **params}
    if api_key:
        query_params["apikey"] = api_key
    query = urllib.parse.urlencode([(key, str(value)) for key, value in query_params.items()], doseq=True)
    response = http_request_json(f"http://127.0.0.1:{port}/api?{query}", timeout=timeout)
    return json_object(response)


def sabnzbd_section_config(payload: dict[str, object], section: str) -> dict[str, object]:
    config = payload.get("config")
    if isinstance(config, dict):
        nested = config.get(section)
        if isinstance(nested, dict):
            return nested
        return config
    return payload


def sabnzbd_category_names(payload: dict[str, object]) -> list[str]:
    raw = payload.get("categories")
    if raw is None:
        raw = payload.get("cats")
    if raw is None:
        raw = sabnzbd_section_config(payload, "categories")
    categories: list[str] = []
    if isinstance(raw, dict):
        for key, value in raw.items():
            name = str((value.get("name") if isinstance(value, dict) else key) or key).strip()
            if name and name not in categories:
                categories.append(name)
        return categories
    if isinstance(raw, list):
        for item in raw:
            if isinstance(item, dict):
                name = str(item.get("name") or item.get("category") or "").strip()
            else:
                name = str(item or "").strip()
            if name and name not in categories:
                categories.append(name)
    return categories


def ensure_sabnzbd_bootstrap(port: int, *, api_key: str, domain_name: str) -> None:
    misc_settings = {
        "host": "0.0.0.0",
        "download_dir": SABNZBD_INCOMPLETE_DOWNLOAD_PATH,
        "complete_dir": SABNZBD_COMPLETE_DOWNLOAD_PATH,
    }
    for keyword, value in misc_settings.items():
        sabnzbd_api_request_json(
            port,
            api_key=api_key,
            mode="set_config",
            section="misc",
            keyword=keyword,
            value=value,
        )
    sabnzbd_api_request_json(
        port,
        api_key=api_key,
        mode="set_config",
        section="special",
        keyword="host_whitelist",
        value=",".join(
            (
                f"sabnzbd.{domain_name}",
                "sabnzbd.media.svc.cluster.local",
                "localhost",
                "127.0.0.1",
            )
        ),
    )
    for category, save_path in ARR_SABNZBD_CATEGORY_SAVE_PATHS.items():
        sabnzbd_api_request_json(
            port,
            api_key=api_key,
            mode="set_config",
            section="categories",
            name=category,
            dir=save_path,
        )
    misc = sabnzbd_section_config(
        sabnzbd_api_request_json(port, api_key=api_key, mode="get_config", section="misc"),
        "misc",
    )
    if str(misc.get("host") or "").strip() != "0.0.0.0":
        raise HaaCError("SABnzbd persisted settings, but it is still not bound to 0.0.0.0.")
    if str(misc.get("download_dir") or "").strip() != SABNZBD_INCOMPLETE_DOWNLOAD_PATH:
        raise HaaCError("SABnzbd persisted settings, but the incomplete download path is still unexpected.")
    if str(misc.get("complete_dir") or "").strip() != SABNZBD_COMPLETE_DOWNLOAD_PATH:
        raise HaaCError("SABnzbd persisted settings, but the complete download path is still unexpected.")
    category_names = sabnzbd_category_names(sabnzbd_api_request_json(port, api_key=api_key, mode="get_cats"))
    missing = sorted(set(ARR_SABNZBD_CATEGORY_SAVE_PATHS) - set(category_names))
    if missing:
        raise HaaCError(f"SABnzbd persisted settings, but categories are still missing: {', '.join(missing)}")
    version_payload = sabnzbd_api_request_json(port, api_key=api_key, mode="version")
    version = str(version_payload.get("version") or "").strip()
    if not version:
        raise HaaCError("SABnzbd API is reachable, but it did not return a version payload.")
    require_http_status(
        f"http://127.0.0.1:{port}/",
        label="SABnzbd /",
        expected_statuses=(200,),
        expected_body_pattern=r"SABnzbd",
    )


def indent_block(text: str, prefix: str = "    ") -> str:
    stripped = text.rstrip("\n")
    if not stripped:
        return prefix.rstrip()
    return "\n".join(f"{prefix}{line}" if line else prefix.rstrip() for line in stripped.splitlines())


def recyclarr_config_text() -> str:
    return RECYCLARR_CONFIG_TEMPLATE.read_text(encoding="utf-8").rstrip() + "\n"


def recyclarr_runtime_secrets_text(*, radarr_api_key: str, sonarr_api_key: str) -> str:
    return (
        f"radarr_main_base_url: {RADARR_INTERNAL_URL}\n"
        f"radarr_main_api_key: {radarr_api_key}\n"
        f"sonarr_main_base_url: {SONARR_INTERNAL_URL}\n"
        f"sonarr_main_api_key: {sonarr_api_key}\n"
    )


def apply_manifest_text(kubectl: str, kubeconfig: Path, manifest: str, *, label: str) -> None:
    completed = run(
        [kubectl, "--kubeconfig", str(kubeconfig), "apply", "-f", "-"],
        capture_output=True,
        check=False,
        input_text=manifest,
    )
    if completed.returncode != 0:
        raise HaaCError(f"{label} apply failed.\n{completed.stderr or completed.stdout}")


def ensure_recyclarr_runtime_secret(
    kubectl: str,
    kubeconfig: Path,
    *,
    radarr_api_key: str,
    sonarr_api_key: str,
    lidarr_api_key: str = "",
    whisparr_api_key: str = "",
    bazarr_api_key: str = "",
    sabnzbd_api_key: str = "",
) -> None:
    lidarr_line = f"  LIDARR_API_KEY: {lidarr_api_key}\n" if lidarr_api_key else ""
    whisparr_line = f"  WHISPARR_API_KEY: {whisparr_api_key}\n" if whisparr_api_key else ""
    bazarr_line = f"  BAZARR_API_KEY: {bazarr_api_key}\n" if bazarr_api_key else ""
    sabnzbd_line = f"  SABNZBD_API_KEY: {sabnzbd_api_key}\n" if sabnzbd_api_key else ""
    manifest = (
        "apiVersion: v1\n"
        "kind: Secret\n"
        "metadata:\n"
        f"  name: {RECYCLARR_SECRET_NAME}\n"
        "  namespace: media\n"
        "type: Opaque\n"
        "stringData:\n"
        f"  RADARR_API_KEY: {radarr_api_key}\n"
        f"  SONARR_API_KEY: {sonarr_api_key}\n"
        f"{lidarr_line}"
        f"{whisparr_line}"
        f"{bazarr_line}"
        f"{sabnzbd_line}"
        "  secrets.yml: |\n"
        f"{indent_block(recyclarr_runtime_secrets_text(radarr_api_key=radarr_api_key, sonarr_api_key=sonarr_api_key))}\n"
    )
    apply_manifest_text(kubectl, kubeconfig, manifest, label="Recyclarr runtime secret")


def run_recyclarr_sync_job(kubectl: str, kubeconfig: Path, *, timeout_seconds: int = 300) -> None:
    job_name = f"recyclarr-sync-{uuid.uuid4().hex[:8]}"
    created = run(
        [
            kubectl,
            "--kubeconfig",
            str(kubeconfig),
            "create",
            "job",
            job_name,
            "--from=cronjob/recyclarr",
            "-n",
            "media",
        ],
        capture_output=True,
        check=False,
    )
    if created.returncode != 0:
        raise HaaCError(f"Recyclarr sync job could not be created.\n{created.stderr or created.stdout}")
    try:
        waited = run(
            [
                kubectl,
                "--kubeconfig",
                str(kubeconfig),
                "wait",
                "--for=condition=complete",
                f"job/{job_name}",
                "-n",
                "media",
                f"--timeout={timeout_seconds}s",
            ],
            capture_output=True,
            check=False,
        )
        if waited.returncode == 0:
            return
        logs = ""
        try:
            pod_name = latest_pod_name(kubectl, kubeconfig, "media", f"job-name={job_name}")
        except HaaCError:
            pod_name = ""
        if pod_name:
            logs = run(
                [kubectl, "--kubeconfig", str(kubeconfig), "logs", "-n", "media", pod_name],
                capture_output=True,
                check=False,
            ).stdout
        raise HaaCError(
            f"Recyclarr sync job failed or timed out.\n{waited.stderr or waited.stdout}\n{logs}".strip()
        )
    finally:
        run(
            [kubectl, "--kubeconfig", str(kubeconfig), "delete", "job", job_name, "-n", "media", "--ignore-not-found=true"],
            capture_output=True,
            check=False,
        )


def verify_recyclarr_sync_surface(port: int, *, app_name: str, api_key: str, expected_profile: str) -> None:
    headers = {"X-Api-Key": api_key}
    quality_profiles = json_array(http_request_json(f"http://127.0.0.1:{port}/api/v3/qualityprofile", headers=headers))
    if not any(str(item.get("name") or "").strip() == expected_profile for item in quality_profiles):
        raise HaaCError(f"{app_name} does not expose the expected Recyclarr-managed quality profile {expected_profile}.")
    custom_formats = json_array(http_request_json(f"http://127.0.0.1:{port}/api/v3/customformat", headers=headers))
    if not custom_formats:
        raise HaaCError(f"{app_name} still exposes no custom formats after Recyclarr sync.")


def seerr_admin_identity(env: dict[str, str]) -> tuple[str, str, str]:
    username = (
        env.get("JELLYFIN_ADMIN_USERNAME")
        or env.get("HAAC_MAIN_USERNAME")
        or env.get("AUTHELIA_ADMIN_USERNAME")
        or "admin"
    ).strip()
    password = (
        env.get("JELLYFIN_ADMIN_PASSWORD")
        or env.get("HAAC_MAIN_PASSWORD")
        or env.get("AUTHELIA_ADMIN_PASSWORD")
        or ""
    ).strip()
    email = (
        env.get("JELLYFIN_ADMIN_EMAIL")
        or env.get("HAAC_MAIN_EMAIL")
        or env.get("AUTHELIA_ADMIN_EMAIL")
        or (f"{username}@{env.get('DOMAIN_NAME', '').strip()}" if env.get("DOMAIN_NAME") else username)
    ).strip()
    if not password:
        raise HaaCError(
            "Seerr bootstrap needs Jellyfin admin credentials. Set JELLYFIN_ADMIN_PASSWORD or let it derive from HAAC_MAIN_PASSWORD."
        )
    return username, password, email


def seerr_public_settings(port: int) -> dict[str, object]:
    response = http_request_json(f"http://127.0.0.1:{port}/api/v1/settings/public")
    if not isinstance(response, dict):
        raise HaaCError("Seerr public settings endpoint returned an unexpected response")
    return response


def seerr_main_settings(port: int, *, opener: urllib.request.OpenerDirector) -> dict[str, object]:
    response = http_request_json(f"http://127.0.0.1:{port}/api/v1/settings/main", opener=opener)
    if not isinstance(response, dict):
        raise HaaCError("Seerr main settings endpoint returned an unexpected response")
    return response


def jellyfin_public_info(port: int) -> dict[str, object]:
    response = http_request_json(f"http://127.0.0.1:{port}/System/Info/Public")
    if not isinstance(response, dict):
        raise HaaCError("Jellyfin public info endpoint returned an unexpected response")
    return response


def jellyfin_startup_incomplete(public_info: dict[str, object]) -> bool:
    return not bool(public_info.get("StartupWizardCompleted"))


def authenticate_jellyfin_admin(port: int, *, username: str, password: str) -> dict[str, object]:
    auth = http_request_json(
        f"http://127.0.0.1:{port}/Users/AuthenticateByName",
        method="POST",
        payload={"Username": username, "Pw": password},
        headers={"Authorization": JELLYFIN_BOOTSTRAP_AUTH_HEADER},
    )
    if not isinstance(auth, dict) or not str(auth.get("AccessToken") or "").strip():
        raise HaaCError("Jellyfin admin authentication did not return an access token.")
    return auth


def jellyfin_auth_headers(access_token: str) -> dict[str, str]:
    return {"Authorization": f"{JELLYFIN_BOOTSTRAP_AUTH_HEADER}, Token={access_token}"}


def jellyfin_virtual_folder_matches(folder: dict[str, object], *, name: str, path: str) -> bool:
    folder_name = str(folder.get("Name") or folder.get("name") or "").strip()
    locations = json_array(folder.get("Locations") if "Locations" in folder else folder.get("locations"))
    return folder_name.lower() == name.lower() or path in [str(item).strip() for item in locations]


def ensure_jellyfin_system_configuration(port: int, *, access_token: str) -> dict[str, object]:
    headers = jellyfin_auth_headers(access_token)
    current = json_object(http_request_json(f"http://127.0.0.1:{port}/System/Configuration", headers=headers))
    payload = copy.deepcopy(current)
    changed = False
    for key, value in JELLYFIN_CONFIGURATION_DEFAULTS.items():
        if str(payload.get(key) or "").strip() != value:
            payload[key] = value
            changed = True
    if changed:
        status, body = http_request_text(
            f"http://127.0.0.1:{port}/System/Configuration",
            method="POST",
            payload=payload,
            headers=headers,
        )
        if status not in (200, 204):
            raise HaaCError(f"Jellyfin system configuration bootstrap failed.\nHTTP {status}\n{body}")
        current = json_object(http_request_json(f"http://127.0.0.1:{port}/System/Configuration", headers=headers))
    for key, value in JELLYFIN_CONFIGURATION_DEFAULTS.items():
        if str(current.get(key) or "").strip() != value:
            raise HaaCError(f"Jellyfin system configuration did not persist {key}={value!r}.")
    return current


def ensure_jellyfin_admin_ready(
    port: int,
    *,
    username: str,
    password: str,
    domain_name: str,
) -> dict[str, object]:
    public_info = jellyfin_public_info(port)
    if jellyfin_startup_incomplete(public_info):
        first_user = http_request_json(f"http://127.0.0.1:{port}/Startup/User")
        if not isinstance(first_user, dict) or not str(first_user.get("Name") or "").strip():
            raise HaaCError("Jellyfin startup user endpoint did not expose an initial user placeholder.")
        current = http_request_json(f"http://127.0.0.1:{port}/Startup/Configuration")
        if not isinstance(current, dict):
            raise HaaCError("Jellyfin startup configuration returned an unexpected response")
        config_payload = {
            "ServerName": str(current.get("ServerName") or f"jellyfin.{domain_name}"),
            **JELLYFIN_CONFIGURATION_DEFAULTS,
        }
        for url, payload in (
            (f"http://127.0.0.1:{port}/Startup/Configuration", config_payload),
            (f"http://127.0.0.1:{port}/Startup/User", {"Name": username, "Password": password}),
        ):
            status, body = http_request_text(url, method="POST", payload=payload)
            if status not in (200, 204):
                raise HaaCError(f"Jellyfin startup bootstrap failed: POST {url}\nHTTP {status}\n{body}")
        status, body = http_request_text(
            f"http://127.0.0.1:{port}/Startup/Complete",
            method="POST",
            headers={"Content-Type": "application/octet-stream"},
        )
        if status not in (200, 204):
            raise HaaCError(f"Jellyfin startup completion failed.\nHTTP {status}\n{body}")
        public_info = jellyfin_public_info(port)
        if jellyfin_startup_incomplete(public_info):
            raise HaaCError("Jellyfin startup wizard is still incomplete after bootstrap reconciliation.")
    authenticate_jellyfin_admin(port, username=username, password=password)
    return public_info


def ensure_jellyfin_libraries(port: int, *, access_token: str) -> list[dict[str, object]]:
    headers = jellyfin_auth_headers(access_token)
    current = http_request_json(f"http://127.0.0.1:{port}/Library/VirtualFolders", headers=headers)
    folders = json_array(current)
    for library in JELLYFIN_DEFAULT_LIBRARIES:
        if any(jellyfin_virtual_folder_matches(folder, name=library["name"], path=library["path"]) for folder in folders):
            continue
        query = urllib.parse.urlencode(
            {
                "name": library["name"],
                "collectionType": library["collectionType"],
                "paths": library["path"],
                "refreshLibrary": "true",
            }
        )
        status, body = http_request_text(
            f"http://127.0.0.1:{port}/Library/VirtualFolders?{query}",
            method="POST",
            headers=headers,
        )
        if status not in (200, 204):
            raise HaaCError(
                f"Jellyfin library bootstrap failed for {library['name']}.\nHTTP {status}\n{body}"
            )
        current = http_request_json(f"http://127.0.0.1:{port}/Library/VirtualFolders", headers=headers)
        folders = json_array(current)
    return folders


def seerr_login_with_jellyfin(
    port: int,
    *,
    username: str,
    password: str,
    email: str,
    public_settings: dict[str, object] | None = None,
) -> urllib.request.OpenerDirector:
    opener = build_cookie_opener()
    payload = {
        "username": username,
        "password": password,
        "email": email,
    }
    try:
        configured_server_type = int((public_settings or {}).get("mediaServerType", 0))
    except (TypeError, ValueError):
        configured_server_type = 0
    if configured_server_type != SEERR_JELLYFIN_SERVER_TYPE:
        payload.update(
            {
                "hostname": SEERR_JELLYFIN_INTERNAL_HOST,
                "port": SEERR_JELLYFIN_INTERNAL_PORT,
                "useSsl": False,
                "urlBase": "",
                "serverType": SEERR_JELLYFIN_SERVER_TYPE,
            }
        )
    status, body = http_request_text(
        f"http://127.0.0.1:{port}/api/v1/auth/jellyfin",
        method="POST",
        payload=payload,
        opener=opener,
    )
    if status < 200 or status >= 300:
        raise HaaCError(
            "Seerr could not authenticate against Jellyfin with the effective Jellyfin admin credentials.\n"
            "Set JELLYFIN_ADMIN_USERNAME/JELLYFIN_ADMIN_PASSWORD explicitly if the Jellyfin admin differs from HAAC_MAIN_*.\n"
            f"HTTP {status}\n{body}"
        )
    return opener


def ensure_seerr_jellyfin_settings(
    opener: urllib.request.OpenerDirector,
    port: int,
    *,
    domain_name: str,
) -> dict[str, object]:
    current = http_request_json(f"http://127.0.0.1:{port}/api/v1/settings/jellyfin", opener=opener)
    if not isinstance(current, dict):
        raise HaaCError("Seerr Jellyfin settings returned an unexpected response")
    api_key = str(current.get("apiKey") or "").strip()
    if not api_key:
        raise HaaCError("Seerr did not expose a Jellyfin API key after Jellyfin admin login.")
    payload = {
        "ip": SEERR_JELLYFIN_INTERNAL_HOST,
        "port": SEERR_JELLYFIN_INTERNAL_PORT,
        "useSsl": False,
        "urlBase": "",
        "externalHostname": f"https://jellyfin.{domain_name}",
        "jellyfinForgotPasswordUrl": f"https://jellyfin.{domain_name}/web/index.html#!/forgotpassword.html",
        "apiKey": api_key,
    }
    saved = http_request_json(
        f"http://127.0.0.1:{port}/api/v1/settings/jellyfin",
        method="POST",
        payload=payload,
        opener=opener,
    )
    if not isinstance(saved, dict):
        raise HaaCError("Seerr could not persist Jellyfin settings")

    sync_url = f"http://127.0.0.1:{port}/api/v1/settings/jellyfin/library?sync=1"
    http_request_json(sync_url, opener=opener)
    refreshed = http_request_json(f"http://127.0.0.1:{port}/api/v1/settings/jellyfin", opener=opener)
    if not isinstance(refreshed, dict):
        raise HaaCError("Seerr Jellyfin settings refresh returned an unexpected response")
    libraries = json_array(refreshed.get("libraries") if isinstance(refreshed, dict) else [])
    library_ids = [str(item.get("id") or "").strip() for item in libraries if str(item.get("id") or "").strip()]
    if library_ids:
        enable_query = urllib.parse.urlencode({"sync": "1", "enable": ",".join(library_ids)})
        http_request_json(f"http://127.0.0.1:{port}/api/v1/settings/jellyfin/library?{enable_query}", opener=opener)
        refreshed = http_request_json(f"http://127.0.0.1:{port}/api/v1/settings/jellyfin", opener=opener)
        if not isinstance(refreshed, dict):
            raise HaaCError("Seerr Jellyfin settings refresh returned an unexpected response")
    return refreshed


def ensure_seerr_main_settings(
    opener: urllib.request.OpenerDirector,
    port: int,
    *,
    domain_name: str,
) -> dict[str, object]:
    current = seerr_main_settings(port, opener=opener)
    desired = {"applicationUrl": f"https://seerr.{domain_name}"}
    if all(str(current.get(key) or "").strip() == str(value).strip() for key, value in desired.items()):
        return current
    saved = http_request_json(
        f"http://127.0.0.1:{port}/api/v1/settings/main",
        method="POST",
        payload=desired,
        opener=opener,
    )
    if not isinstance(saved, dict):
        raise HaaCError("Seerr could not persist its main settings")
    refreshed = seerr_main_settings(port, opener=opener)
    for key, value in desired.items():
        if str(refreshed.get(key) or "").strip() != str(value).strip():
            raise HaaCError(f"Seerr main settings did not persist {key}={value!r}.")
    return refreshed


def ensure_seerr_radarr_settings(
    opener: urllib.request.OpenerDirector,
    port: int,
    *,
    domain_name: str,
    radarr_api_key: str,
    fallback_root_folders: list[dict[str, object]] | None = None,
) -> None:
    current = http_request_json(f"http://127.0.0.1:{port}/api/v1/settings/radarr", opener=opener)
    existing = json_array(current)
    if existing:
        return
    test_payload = {
        "hostname": "radarr.media.svc.cluster.local",
        "port": 80,
        "apiKey": radarr_api_key,
        "baseUrl": "",
        "useSsl": False,
    }
    test_response = http_request_json(
        f"http://127.0.0.1:{port}/api/v1/settings/radarr/test",
        method="POST",
        payload=test_payload,
        opener=opener,
    )
    if not isinstance(test_response, dict):
        raise HaaCError("Seerr Radarr test did not return a valid response")
    profiles = json_array(test_response.get("profiles"))
    root_folders = json_array(test_response.get("rootFolders"))
    if not root_folders and fallback_root_folders:
        root_folders = fallback_root_folders
    tags = json_array(test_response.get("tags"))
    profile = preferred_option(profiles, name_preferences=("Any", "HD-1080p"))
    root_folder = preferred_option(root_folders, path_preferences=("/data/media/movies", "/data/movies"))
    payload = {
        "name": "Radarr",
        "hostname": test_payload["hostname"],
        "port": 80,
        "apiKey": radarr_api_key,
        "useSsl": False,
        "baseUrl": str(test_response.get("urlBase") or ""),
        "activeProfileId": int(profile.get("id") or 0),
        "activeProfileName": str(profile.get("name") or "default"),
        "activeDirectory": str(root_folder.get("path") or ""),
        "is4k": False,
        "minimumAvailability": "released",
        "tags": [int(tag.get("id") or 0) for tag in tags if str(tag.get("id") or "").isdigit()],
        "isDefault": True,
        "externalUrl": f"https://radarr.{domain_name}",
        "syncEnabled": True,
        "preventSearch": False,
        "tagRequests": True,
    }
    if not payload["activeProfileId"] or not payload["activeDirectory"]:
        raise HaaCError("Seerr Radarr bootstrap could not resolve a usable quality profile or root folder.")
    http_request_json(
        f"http://127.0.0.1:{port}/api/v1/settings/radarr",
        method="POST",
        payload=payload,
        opener=opener,
    )


def ensure_seerr_sonarr_settings(
    opener: urllib.request.OpenerDirector,
    port: int,
    *,
    domain_name: str,
    sonarr_api_key: str,
    fallback_root_folders: list[dict[str, object]] | None = None,
) -> None:
    current = http_request_json(f"http://127.0.0.1:{port}/api/v1/settings/sonarr", opener=opener)
    existing = json_array(current)
    if existing:
        return
    test_payload = {
        "hostname": "sonarr.media.svc.cluster.local",
        "port": 80,
        "apiKey": sonarr_api_key,
        "baseUrl": "",
        "useSsl": False,
    }
    test_response = http_request_json(
        f"http://127.0.0.1:{port}/api/v1/settings/sonarr/test",
        method="POST",
        payload=test_payload,
        opener=opener,
    )
    if not isinstance(test_response, dict):
        raise HaaCError("Seerr Sonarr test did not return a valid response")
    profiles = json_array(test_response.get("profiles"))
    root_folders = json_array(test_response.get("rootFolders"))
    if not root_folders and fallback_root_folders:
        root_folders = fallback_root_folders
    language_profiles = json_array(test_response.get("languageProfiles"))
    tags = [int(tag.get("id") or 0) for tag in json_array(test_response.get("tags")) if str(tag.get("id") or "").isdigit()]
    profile = preferred_option(profiles, name_preferences=("Any", "HD-1080p"))
    root_folder = preferred_option(root_folders, path_preferences=("/data/media/tv", "/data/tv"))
    language_profile = language_profiles[0] if language_profiles else {}
    language_id = int(language_profile.get("id") or 0) if language_profile else 0
    payload = {
        "name": "Sonarr",
        "hostname": test_payload["hostname"],
        "port": 80,
        "apiKey": sonarr_api_key,
        "useSsl": False,
        "baseUrl": str(test_response.get("urlBase") or ""),
        "activeProfileId": int(profile.get("id") or 0),
        "activeProfileName": str(profile.get("name") or "default"),
        "activeDirectory": str(root_folder.get("path") or ""),
        "seriesType": "standard",
        "animeSeriesType": "anime",
        "activeAnimeProfileId": int(profile.get("id") or 0),
        "activeAnimeProfileName": str(profile.get("name") or "default"),
        "activeAnimeDirectory": str(root_folder.get("path") or ""),
        "tags": tags,
        "animeTags": tags,
        "is4k": False,
        "isDefault": True,
        "enableSeasonFolders": True,
        "externalUrl": f"https://sonarr.{domain_name}",
        "syncEnabled": True,
        "preventSearch": False,
        "tagRequests": True,
        "monitorNewItems": "all",
    }
    if language_id:
        payload["activeLanguageProfileId"] = language_id
        payload["activeAnimeLanguageProfileId"] = language_id
    if not payload["activeProfileId"] or not payload["activeDirectory"]:
        raise HaaCError("Seerr Sonarr bootstrap could not resolve a usable quality profile or root folder.")
    http_request_json(
        f"http://127.0.0.1:{port}/api/v1/settings/sonarr",
        method="POST",
        payload=payload,
        opener=opener,
    )


def bazarr_auth_identity(env: dict[str, str]) -> tuple[str, str]:
    username = str(env.get("BAZARR_AUTH_USERNAME") or "").strip()
    password = str(env.get("BAZARR_AUTH_PASSWORD") or "").strip()
    if not username or not password:
        raise HaaCError(
            "Bazarr bootstrap needs native auth credentials. Set BAZARR_AUTH_USERNAME/BAZARR_AUTH_PASSWORD or let them derive from HAAC_MAIN_*."
        )
    return username, password


def bazarr_language_codes(env: dict[str, str]) -> list[str]:
    raw = str(env.get("BAZARR_LANGUAGES") or "").strip()
    values = raw.split(",") if raw else list(BAZARR_DEFAULT_LANGUAGE_CODES)
    codes: list[str] = []
    for value in values:
        code = str(value).strip().lower()
        if not code:
            continue
        if not re.fullmatch(r"[a-z]{2,3}", code):
            raise HaaCError(f"BAZARR_LANGUAGES contains an unsupported language code: {code}")
        if code not in codes:
            codes.append(code)
    if not codes:
        return list(BAZARR_DEFAULT_LANGUAGE_CODES)
    return codes


def bazarr_profile_name(language_codes: list[str]) -> str:
    labels = {
        "en": "English",
        "it": "Italian",
    }
    resolved = [labels.get(code, code.upper()) for code in language_codes]
    return " + ".join(resolved)


def bazarr_default_profile_payload(language_codes: list[str]) -> list[dict[str, object]]:
    return [
        {
            "name": bazarr_profile_name(language_codes),
            "profileId": BAZARR_DEFAULT_PROFILE_ID,
            "cutoff": None,
            "items": [
                {
                    "id": index,
                    "language": code,
                    "forced": False,
                    "hi": False,
                    "audio_exclude": False,
                    "audio_only_include": False,
                }
                for index, code in enumerate(language_codes, start=1)
            ],
            "mustContain": [],
            "mustNotContain": [],
            "originalFormat": False,
            "tag": None,
        }
    ]


def bazarr_api_headers(api_key: str) -> dict[str, str]:
    return {"X-API-KEY": api_key}


def bazarr_settings_json(port: int, *, api_key: str) -> dict[str, object]:
    data = http_request_json(
        f"http://127.0.0.1:{port}/api/system/settings",
        headers=bazarr_api_headers(api_key),
    )
    if not isinstance(data, dict):
        raise HaaCError("Bazarr returned an unsupported settings payload.")
    return data


def read_bazarr_service_api_key(kubectl: str, kubeconfig: Path) -> str:
    pod_name = latest_pod_name(kubectl, kubeconfig, "media", "app=bazarr")
    script = r"""
set -eu
python3 <<'PY'
from pathlib import Path
import re

candidates = [
    Path("/config/config/config.yaml"),
    Path("/config/config/config.yml"),
    Path("/app/config/config.yaml"),
    Path("/app/config/config.yml"),
]
config_path = next((candidate for candidate in candidates if candidate.is_file()), None)
if config_path is None:
    for root in (Path("/config"), Path("/app/config")):
        if not root.exists():
            continue
        for name in ("config.yaml", "config.yml"):
            matches = sorted(root.rglob(name))
            if matches:
                config_path = matches[0]
                break
        if config_path is not None:
            break
if config_path is None:
    raise SystemExit("Bazarr config.yaml not found under /config or /app/config")
text = config_path.read_text(encoding="utf-8")
match = re.search(r"(?ms)^auth:\s*$.*?^[ \t]+apikey:\s*[\"']?([^\"'\n]+)", text)
if not match:
    raise SystemExit("Bazarr config does not expose an API key yet.")
print(match.group(1).strip())
PY
"""
    api_key = kubectl_exec_stdout(
        kubectl,
        kubeconfig,
        namespace="media",
        pod=pod_name,
        container="bazarr",
        script=script,
    ).strip()
    if not api_key:
        raise HaaCError("Bazarr config does not expose an API key yet.")
    return api_key


def bazarr_settings_form_fields(
    *,
    env: dict[str, str],
    radarr_api_key: str,
    sonarr_api_key: str,
) -> list[tuple[str, object]]:
    language_codes = bazarr_language_codes(env)
    fields: list[tuple[str, object]] = [
        ("settings-general-use_sonarr", True),
        ("settings-general-use_radarr", True),
        ("settings-general-single_language", False),
        ("settings-general-minimum_score", 90),
        ("settings-general-minimum_score_movie", 90),
        ("settings-general-serie_default_enabled", True),
        ("settings-general-serie_default_profile", BAZARR_DEFAULT_PROFILE_ID),
        ("settings-general-movie_default_enabled", True),
        ("settings-general-movie_default_profile", BAZARR_DEFAULT_PROFILE_ID),
        ("settings-sonarr-ip", "sonarr.media.svc.cluster.local"),
        ("settings-sonarr-port", 80),
        ("settings-sonarr-base_url", ""),
        ("settings-sonarr-ssl", False),
        ("settings-sonarr-apikey", sonarr_api_key),
        ("settings-sonarr-only_monitored", True),
        ("settings-radarr-ip", "radarr.media.svc.cluster.local"),
        ("settings-radarr-port", 80),
        ("settings-radarr-base_url", ""),
        ("settings-radarr-ssl", False),
        ("settings-radarr-apikey", radarr_api_key),
        ("settings-radarr-only_monitored", True),
        ("languages-profiles", json.dumps(bazarr_default_profile_payload(language_codes))),
    ]
    for code in language_codes:
        fields.append(("languages-enabled", code))
    return fields


def ensure_bazarr_bootstrap(
    port: int,
    *,
    env: dict[str, str],
    api_key: str,
    radarr_api_key: str,
    sonarr_api_key: str,
) -> None:
    settings_url = f"http://127.0.0.1:{port}/api/system/settings"
    status, body = http_request_form_text(
        settings_url,
        fields=bazarr_settings_form_fields(env=env, radarr_api_key=radarr_api_key, sonarr_api_key=sonarr_api_key),
        headers=bazarr_api_headers(api_key),
    )
    if status not in (200, 204):
        raise HaaCError(f"Bazarr settings bootstrap failed.\nHTTP {status}\n{body}")

    username, password = bazarr_auth_identity(env)
    auth_status, auth_body = http_request_form_text(
        settings_url,
        fields=[
            ("settings-auth-type", "form"),
            ("settings-auth-username", username),
            ("settings-auth-password", password),
        ],
        headers=bazarr_api_headers(api_key),
    )
    if auth_status not in (200, 204):
        raise HaaCError(f"Bazarr auth bootstrap failed.\nHTTP {auth_status}\n{auth_body}")

    settings = bazarr_settings_json(port, api_key=api_key)
    general = settings.get("general") if isinstance(settings.get("general"), dict) else {}
    sonarr_settings = settings.get("sonarr") if isinstance(settings.get("sonarr"), dict) else {}
    radarr_settings = settings.get("radarr") if isinstance(settings.get("radarr"), dict) else {}
    auth_settings = settings.get("auth") if isinstance(settings.get("auth"), dict) else {}
    if not bool(general.get("use_sonarr")) or not bool(general.get("use_radarr")):
        raise HaaCError("Bazarr persisted settings but still does not enable both Sonarr and Radarr.")
    if str(sonarr_settings.get("ip") or "").strip() != "sonarr.media.svc.cluster.local":
        raise HaaCError("Bazarr settings persisted, but the Sonarr endpoint is still not the repo-managed internal service.")
    if str(radarr_settings.get("ip") or "").strip() != "radarr.media.svc.cluster.local":
        raise HaaCError("Bazarr settings persisted, but the Radarr endpoint is still not the repo-managed internal service.")
    if not bool(general.get("serie_default_enabled")) or not bool(general.get("movie_default_enabled")):
        raise HaaCError("Bazarr settings persisted, but the default language profile is still disabled for series or movies.")
    if str(auth_settings.get("type") or "").strip() != "form":
        raise HaaCError("Bazarr settings persisted, but native form authentication is still disabled.")
    require_http_status(
        f"http://127.0.0.1:{port}/login",
        label="Bazarr /login",
        expected_statuses=(200, 302),
    )


def warm_flaresolverr_metrics(kubectl: str, kubeconfig: Path) -> None:
    with kubectl_port_forward(kubectl, kubeconfig, "media", "svc/flaresolverr", 8191) as app_port:
        http_request_text(
            f"http://127.0.0.1:{app_port}/v1",
            method="POST",
            payload={"cmd": "request.get", "url": "https://example.com", "maxTimeout": 60000},
        )


def verify_media_metrics_surface(kubectl: str, kubeconfig: Path) -> None:
    metric_checks = (
        ("svc/flaresolverr", 8192, "flaresolverr_request_total"),
        ("svc/radarr", 9707, "radarr_movie_total"),
        ("svc/sonarr", 9708, "sonarr_series_total"),
        ("svc/prowlarr", 9709, "prowlarr_indexer_total"),
        ("svc/lidarr", 9711, "lidarr_artists_total"),
        ("svc/sabnzbd", 9712, "sabnzbd_info"),
        ("svc/autobrr", 9074, "autobrr_info"),
        ("svc/bazarr-metrics", 9710, "bazarr_system_status"),
        ("svc/unpackerr", 5656, "unpackerr_uptime_seconds_total"),
    )
    for resource, remote_port, metric_name in metric_checks:
        with kubectl_port_forward(kubectl, kubeconfig, "media", resource, remote_port) as local_port:
            body = require_http_status(
                f"http://127.0.0.1:{local_port}/metrics",
                label=f"{resource} metrics",
                expected_statuses=(200,),
            )
            if metric_name not in body:
                raise HaaCError(f"{resource} metrics endpoint is reachable, but {metric_name} is still absent.")


def ensure_media_storage_path(
    kubectl: str,
    kubeconfig: Path,
    *,
    container_name: str,
    path: str,
) -> None:
    pod_name = latest_pod_name(kubectl, kubeconfig, "media", f"app={container_name}")
    quoted_path = shlex.quote(path)
    kubectl_exec_stdout(
        kubectl,
        kubeconfig,
        namespace="media",
        pod=pod_name,
        container=container_name,
        script=f"mkdir -p {quoted_path} && printf ready",
    )


def normalize_media_title(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", str(value or "").lower())


def release_mentions_candidate(title: str, *, candidate_title: str, year: int) -> bool:
    normalized_release = normalize_media_title(title)
    normalized_candidate = normalize_media_title(candidate_title)
    return bool(normalized_candidate and normalized_candidate in normalized_release and str(year) in str(title or ""))


def arr_verifier_release_penalty(title: str) -> int:
    normalized = normalize_media_title(title)
    return 1 if any(token in normalized for token in ARR_VERIFIER_AVOID_RELEASE_TOKENS) else 0


def seerr_search_results(
    port: int,
    *,
    opener: urllib.request.OpenerDirector,
    query: str,
) -> list[dict[str, object]]:
    response = http_request_json(
        f"http://127.0.0.1:{port}/api/v1/search?query={urllib.parse.quote(query)}",
        opener=opener,
    )
    if isinstance(response, dict):
        return json_array(response.get("results") if "results" in response else [])
    return []


def exact_seerr_movie_match(
    results: list[dict[str, object]],
    *,
    title: str,
    year: int,
    tmdb_id: int | None = None,
) -> dict[str, object]:
    exact_matches: list[dict[str, object]] = []
    for item in results:
        if str(item.get("mediaType") or "").strip() != "movie":
            continue
        if normalize_media_title(item.get("title") or item.get("originalTitle") or "") != normalize_media_title(title):
            continue
        release_year = str(item.get("releaseDate") or "").strip()[:4]
        if release_year != str(year):
            continue
        exact_matches.append(item)
    if tmdb_id:
        for item in exact_matches:
            if int(item.get("id") or 0) == int(tmdb_id):
                return item
    return exact_matches[0] if exact_matches else {}


def prowlarr_search_results(
    port: int,
    *,
    api_key: str,
    query: str,
) -> list[dict[str, object]]:
    response = http_request_json(
        f"http://127.0.0.1:{port}/api/v1/search?query={urllib.parse.quote(query)}&type=search&categories=2000",
        headers={"X-Api-Key": api_key},
    )
    return json_array(response)


def exact_seeded_prowlarr_releases(
    results: list[dict[str, object]],
    *,
    candidate_title: str,
    year: int,
    preferred_max_size_bytes: int = ARR_VERIFIER_PREFERRED_MAX_SIZE_BYTES,
) -> list[dict[str, object]]:
    matches: list[dict[str, object]] = []
    for item in results:
        title = str(item.get("title") or "").strip()
        if not release_mentions_candidate(title, candidate_title=candidate_title, year=year):
            continue
        if int(item.get("seeders") or 0) <= 0:
            continue
        matches.append(item)
    matches.sort(
        key=lambda item: (
            arr_verifier_release_penalty(str(item.get("title") or "")),
            0 if 0 < int(item.get("size") or 0) <= preferred_max_size_bytes else 1,
            -int(item.get("seeders") or 0),
            int(item.get("size") or 0) or sys.maxsize,
            str(item.get("title") or ""),
        )
    )
    return matches


def arr_verifier_candidate_rank(
    movie: dict[str, object],
    prowlarr_matches: list[dict[str, object]],
    *,
    preferred_max_size_bytes: int = ARR_VERIFIER_PREFERRED_MAX_SIZE_BYTES,
) -> tuple[int, int, int, int, str]:
    best_release = prowlarr_matches[0] if prowlarr_matches else {}
    if movie and bool(movie.get("hasFile")):
        lifecycle_rank = 0
    elif not movie:
        lifecycle_rank = 1
    else:
        lifecycle_rank = 2
    return (
        lifecycle_rank,
        arr_verifier_release_penalty(str(best_release.get("title") or "")),
        0 if 0 < int(best_release.get("size") or 0) <= preferred_max_size_bytes else 1,
        -int(best_release.get("seeders") or 0),
        int(best_release.get("size") or 0) or sys.maxsize,
        str(best_release.get("title") or ""),
    )


def choose_arr_verifier_candidate(
    seerr_port: int,
    *,
    seerr_opener: urllib.request.OpenerDirector,
    prowlarr_port: int,
    prowlarr_api_key: str,
    radarr_port: int,
    radarr_api_key: str,
) -> tuple[dict[str, object], dict[str, object], list[dict[str, object]]]:
    ranked_matches: list[tuple[tuple[int, int, int, int, str], dict[str, object], dict[str, object], list[dict[str, object]]]] = []
    for candidate in ARR_VERIFIER_CANDIDATES:
        seerr_match = exact_seerr_movie_match(
            seerr_search_results(seerr_port, opener=seerr_opener, query=str(candidate["query"])),
            title=str(candidate["title"]),
            year=int(candidate["year"]),
            tmdb_id=int(candidate["tmdbId"]),
        )
        if not seerr_match:
            continue
        prowlarr_matches = exact_seeded_prowlarr_releases(
            prowlarr_search_results(
                prowlarr_port,
                api_key=prowlarr_api_key,
                query=f"{candidate['title']} {candidate['year']}",
            ),
            candidate_title=str(candidate["title"]),
            year=int(candidate["year"]),
        )
        if prowlarr_matches:
            movie = radarr_movie_by_tmdb_id(radarr_port, api_key=radarr_api_key, tmdb_id=int(candidate["tmdbId"]))
            ranked_matches.append(
                (
                    arr_verifier_candidate_rank(movie, prowlarr_matches),
                    candidate,
                    seerr_match,
                    prowlarr_matches,
                )
            )
    if ranked_matches:
        ranked_matches.sort(key=lambda item: item[0])
        _, candidate, seerr_match, prowlarr_matches = ranked_matches[0]
        return candidate, seerr_match, prowlarr_matches
    raise HaaCError(
        "ARR end-to-end verification failed.\n"
        "Furthest verified stage: Seerr and Prowlarr reachability\n"
        "Blocker: title availability\n"
        "No curated safe title currently resolves in Seerr and returns seeded exact-match movie releases from Prowlarr."
    )


def radarr_movies(port: int, *, api_key: str) -> list[dict[str, object]]:
    return json_array(http_request_json(f"http://127.0.0.1:{port}/api/v3/movie", headers={"X-Api-Key": api_key}))


def radarr_movie_by_tmdb_id(port: int, *, api_key: str, tmdb_id: int) -> dict[str, object]:
    for item in radarr_movies(port, api_key=api_key):
        if int(item.get("tmdbId") or 0) == int(tmdb_id):
            return item
    return {}


def wait_for_radarr_movie(
    port: int,
    *,
    api_key: str,
    tmdb_id: int,
    timeout_seconds: int = 180,
) -> dict[str, object]:
    deadline = time.time() + timeout_seconds
    while time.time() < deadline:
        movie = radarr_movie_by_tmdb_id(port, api_key=api_key, tmdb_id=tmdb_id)
        if movie:
            return movie
        time.sleep(ARR_VERIFIER_POLL_SECONDS)
    return {}


def radarr_release_records(
    port: int,
    *,
    api_key: str,
    movie_id: int,
) -> list[dict[str, object]]:
    response = http_request_json(
        f"http://127.0.0.1:{port}/api/v3/release?movieId={movie_id}&includeRejected=true",
        headers={"X-Api-Key": api_key},
    )
    return json_array(response)


def exact_radarr_release_matches(
    releases: list[dict[str, object]],
    *,
    candidate_title: str,
    year: int,
) -> list[dict[str, object]]:
    return [
        item
        for item in releases
        if release_mentions_candidate(str(item.get("title") or ""), candidate_title=candidate_title, year=year)
    ]


def preferred_arr_verifier_release(
    releases: list[dict[str, object]],
    *,
    preferred_max_size_bytes: int = ARR_VERIFIER_PREFERRED_MAX_SIZE_BYTES,
) -> dict[str, object]:
    if not releases:
        return {}
    sorted_releases = sorted(
        releases,
        key=lambda item: (
            arr_verifier_release_penalty(str(item.get("title") or "")),
            0 if bool(item.get("downloadAllowed")) else 1,
            0 if 0 < int(item.get("size") or 0) <= preferred_max_size_bytes else 1,
            -int(item.get("seeders") or 0),
            int(item.get("size") or 0) or sys.maxsize,
            str(item.get("title") or ""),
        ),
    )
    return sorted_releases[0]


def trigger_radarr_release_download(port: int, *, api_key: str, release: dict[str, object]) -> dict[str, object]:
    response = http_request_json(
        f"http://127.0.0.1:{port}/api/v3/release",
        method="POST",
        payload=release,
        headers={"X-Api-Key": api_key},
    )
    return json_object(response)


def radarr_queue_records(port: int, *, api_key: str) -> list[dict[str, object]]:
    response = http_request_json(f"http://127.0.0.1:{port}/api/v3/queue", headers={"X-Api-Key": api_key})
    return json_array(response.get("records") if isinstance(response, dict) else [])


def radarr_history_records(port: int, *, api_key: str) -> list[dict[str, object]]:
    response = http_request_json(f"http://127.0.0.1:{port}/api/v3/history", headers={"X-Api-Key": api_key})
    return json_array(response.get("records") if isinstance(response, dict) else [])


def radarr_movie_files(port: int, *, api_key: str, movie_id: int) -> list[dict[str, object]]:
    response = http_request_json(
        f"http://127.0.0.1:{port}/api/v3/moviefile?movieId={movie_id}",
        headers={"X-Api-Key": api_key},
    )
    return json_array(response)


def match_release_title(record_title: str, selected_title: str) -> bool:
    return normalize_media_title(record_title) == normalize_media_title(selected_title)


def container_media_path_to_host_nas_path(container_path: str, *, host_nas_path: str) -> PurePosixPath:
    root = PurePosixPath(host_nas_path)
    relative = PurePosixPath(container_path).relative_to(PurePosixPath("/data"))
    return root / relative


def proxmox_host_path_exists(proxmox_host: str, path: PurePosixPath) -> bool:
    completed = run(
        proxmox_ssh_command(proxmox_host, f"test -f {shlex.quote(str(path))} && printf present"),
        check=False,
        capture_output=True,
    )
    return completed.returncode == 0 and "present" in (completed.stdout or "")


def jellyfin_refresh_library(port: int, *, access_token: str) -> None:
    status, body = http_request_text(
        f"http://127.0.0.1:{port}/Library/Refresh",
        method="POST",
        headers=jellyfin_auth_headers(access_token),
    )
    if status not in (200, 202, 204):
        raise HaaCError(f"Jellyfin library refresh failed.\nHTTP {status}\n{body}")


def jellyfin_search_movie_items(
    port: int,
    *,
    access_token: str,
    title: str,
    user_id: str = "",
) -> list[dict[str, object]]:
    query = {
        "SearchTerm": title,
        "Recursive": "true",
        "IncludeItemTypes": "Movie",
        "Fields": "Path",
    }
    if user_id:
        query["userId"] = user_id
    response = http_request_json(
        f"http://127.0.0.1:{port}/Items?{urllib.parse.urlencode(query)}",
        headers=jellyfin_auth_headers(access_token),
    )
    return json_array(response.get("Items") if isinstance(response, dict) else [])


def exact_jellyfin_movie_match(
    items: list[dict[str, object]],
    *,
    title: str,
    year: int,
) -> dict[str, object]:
    for item in items:
        item_title = str(item.get("Name") or item.get("name") or "").strip()
        item_year = int(item.get("ProductionYear") or item.get("productionYear") or 0)
        if normalize_media_title(item_title) == normalize_media_title(title) and item_year == int(year):
            return item
    return {}


def arr_verifier_failure(*, furthest_verified: str, blocker: str, detail: str) -> None:
    raise HaaCError(
        "ARR end-to-end verification failed.\n"
        f"Furthest verified stage: {furthest_verified}\n"
        f"Blocker: {blocker}\n"
        f"{detail}"
    )


def verify_arr_flow(master_ip: str, proxmox_host: str, kubeconfig: Path, kubectl: str, *, timeout_seconds: int = 1800) -> None:
    env = merged_env()
    require_env(["DOMAIN_NAME", "QUI_PASSWORD", "HOST_NAS_PATH"], env)
    downloader_username = env.get("QBITTORRENT_USERNAME", "admin").strip() or "admin"
    downloader_password = env["QUI_PASSWORD"].strip()
    username, password, email = seerr_admin_identity(env)
    host_nas_path = env["HOST_NAS_PATH"].strip()

    with cluster_session(proxmox_host, master_ip, kubeconfig, kubectl) as session_kubeconfig:
        print("[stage] ARR candidate selection")
        prowlarr_api_key = read_arr_service_api_key(kubectl, session_kubeconfig, "prowlarr")
        radarr_api_key = read_arr_service_api_key(kubectl, session_kubeconfig, "radarr")
        with kubectl_port_forward(kubectl, session_kubeconfig, "media", "svc/seerr", 80) as seerr_port, kubectl_port_forward(
            kubectl, session_kubeconfig, "media", "svc/prowlarr", 80
        ) as prowlarr_port, kubectl_port_forward(kubectl, session_kubeconfig, "media", "svc/radarr", 80) as radarr_port:
            seerr_opener = seerr_login_with_jellyfin(
                seerr_port,
                username=username,
                password=password,
                email=email,
                public_settings=seerr_public_settings(seerr_port),
            )
            candidate, seerr_match, seeded_prowlarr_results = choose_arr_verifier_candidate(
                seerr_port,
                seerr_opener=seerr_opener,
                prowlarr_port=prowlarr_port,
                prowlarr_api_key=prowlarr_api_key,
                radarr_port=radarr_port,
                radarr_api_key=radarr_api_key,
            )
            candidate_title = str(candidate["title"])
            candidate_year = int(candidate["year"])
            candidate_tmdb_id = int(candidate["tmdbId"])
            media_info = json_object(seerr_match.get("mediaInfo") if isinstance(seerr_match, dict) else {})
            if not media_info:
                status, body = http_request_text(
                    f"http://127.0.0.1:{seerr_port}/api/v1/request",
                    method="POST",
                    payload={"mediaType": "movie", "mediaId": candidate_tmdb_id},
                    opener=seerr_opener,
                )
                if status not in (200, 201, 202):
                    arr_verifier_failure(
                        furthest_verified="Safe candidate selection",
                        blocker="title availability",
                        detail=f"Seerr could not create the movie request for {candidate_title} ({candidate_year}).\nHTTP {status}\n{body}",
                    )
            print(f"[ok] ARR candidate selection: {candidate_title} ({candidate_year})")

        print("[stage] ARR request and release handoff")
        with kubectl_port_forward(kubectl, session_kubeconfig, "media", "svc/radarr", 80) as radarr_port:
            movie = wait_for_radarr_movie(radarr_port, api_key=radarr_api_key, tmdb_id=candidate_tmdb_id)
            if not movie:
                arr_verifier_failure(
                    furthest_verified="Seerr request creation",
                    blocker="search/indexer drift",
                    detail=f"Radarr did not materialize the requested movie for TMDb {candidate_tmdb_id} before timeout.",
                )
            movie_id = int(movie.get("id") or 0)
            history_records = [
                item for item in radarr_history_records(radarr_port, api_key=radarr_api_key) if int(item.get("movieId") or 0) == movie_id
            ]
            if bool(movie.get("hasFile")):
                selected_title = str(next((item.get("sourceTitle") for item in history_records if str(item.get("eventType") or "").lower() == "grabbed"), "") or candidate_title).strip()
                print(f"[ok] ARR request and release handoff: existing imported candidate {selected_title}")
            else:
                releases = exact_radarr_release_matches(
                    radarr_release_records(radarr_port, api_key=radarr_api_key, movie_id=movie_id),
                    candidate_title=candidate_title,
                    year=candidate_year,
                )
                preferred_title = str(seeded_prowlarr_results[0].get("title") or "").strip() if seeded_prowlarr_results else ""
                preferred_matches = [
                    item for item in releases if preferred_title and match_release_title(str(item.get("title") or ""), preferred_title)
                ]
                selected_release = preferred_arr_verifier_release(preferred_matches or releases)
                if not selected_release:
                    arr_verifier_failure(
                        furthest_verified="Seerr request creation",
                        blocker="search/indexer drift",
                        detail=f"Radarr found no exact-match release candidates for {candidate_title} ({candidate_year}).",
                    )
                selected_title = str(selected_release.get("title") or "").strip()
                queue_records = [item for item in radarr_queue_records(radarr_port, api_key=radarr_api_key) if int(item.get("movieId") or 0) == movie_id]
                already_selected = any(match_release_title(str(item.get("title") or ""), selected_title) for item in queue_records) or any(
                    match_release_title(str(item.get("sourceTitle") or ""), selected_title) for item in history_records
                )
                if not already_selected:
                    trigger_radarr_release_download(radarr_port, api_key=radarr_api_key, release=selected_release)
                print(f"[ok] ARR request and release handoff: {selected_title}")

        print("[stage] Downloader and NAS import")
        torrent_match: dict[str, object] = {}
        imported_file_path = ""
        imported_host_path: PurePosixPath | None = None
        deadline = time.time() + timeout_seconds
        while time.time() < deadline:
            with kubectl_port_forward(kubectl, session_kubeconfig, "media", "svc/qbittorrent", 8080) as qbit_port:
                qbit_opener = qbittorrent_login_via_port_forward(
                    qbit_port,
                    username=downloader_username,
                    password=downloader_password,
                )
                torrents = qbittorrent_torrents_info(qbit_port, opener=qbit_opener)
                torrent_match = next(
                    (
                        item
                        for item in torrents
                        if match_release_title(str(item.get("name") or ""), selected_title)
                    ),
                    {},
                )
            with kubectl_port_forward(kubectl, session_kubeconfig, "media", "svc/radarr", 80) as radarr_port:
                movie = radarr_movie_by_tmdb_id(radarr_port, api_key=radarr_api_key, tmdb_id=candidate_tmdb_id)
                if movie and bool(movie.get("hasFile")):
                    files = radarr_movie_files(radarr_port, api_key=radarr_api_key, movie_id=int(movie.get("id") or 0))
                    if files:
                        imported_file_path = str(files[0].get("path") or "").strip()
                    if imported_file_path:
                        imported_host_path = container_media_path_to_host_nas_path(
                            imported_file_path,
                            host_nas_path=host_nas_path,
                        )
                        if proxmox_host_path_exists(proxmox_host, imported_host_path):
                            print(f"[ok] Downloader and NAS import: {imported_host_path}")
                            break
            time.sleep(ARR_VERIFIER_POLL_SECONDS)
        else:
            if not torrent_match:
                arr_verifier_failure(
                    furthest_verified="Radarr release handoff",
                    blocker="downloader/VPN drift",
                    detail=f"qBittorrent never exposed the selected release {selected_title!r} through the managed VPN-backed downloader path.",
                )
            if float(torrent_match.get("progress") or 0.0) < 1.0:
                arr_verifier_failure(
                    furthest_verified="qBittorrent handoff",
                    blocker="downloader/VPN drift",
                    detail=(
                        f"qBittorrent is still stuck before completion for {selected_title!r}. "
                        f"State={torrent_match.get('state')!r} progress={float(torrent_match.get('progress') or 0.0):.3f} "
                        f"speed={int(torrent_match.get('dlspeed') or 0)}B/s."
                    ),
                )
            arr_verifier_failure(
                furthest_verified="qBittorrent download completion",
                blocker="NAS/import drift",
                detail=f"Radarr did not import {selected_title!r} into the NAS-backed media tree before timeout.",
            )

        print("[stage] Jellyfin visibility")
        with kubectl_port_forward(kubectl, session_kubeconfig, "media", "svc/jellyfin", 80) as jellyfin_port:
            jellyfin_auth = authenticate_jellyfin_admin(jellyfin_port, username=username, password=password)
            access_token = str(jellyfin_auth["AccessToken"])
            user_id = str(json_object(jellyfin_auth.get("User")).get("Id") or "").strip()
            jellyfin_refresh_library(jellyfin_port, access_token=access_token)
            jellyfin_deadline = time.time() + min(timeout_seconds, 600)
            while time.time() < jellyfin_deadline:
                items = jellyfin_search_movie_items(
                    jellyfin_port,
                    access_token=access_token,
                    title=candidate_title,
                    user_id=user_id,
                )
                exact_item = exact_jellyfin_movie_match(items, title=candidate_title, year=candidate_year)
                if exact_item:
                    print(
                        "[ok] Jellyfin visibility: "
                        + json.dumps(
                            {
                                "title": candidate_title,
                                "year": candidate_year,
                                "release": selected_title,
                                "nasPath": str(imported_host_path) if imported_host_path else "",
                                "jellyfinItemId": exact_item.get("Id") or exact_item.get("id") or "",
                            }
                        )
                    )
                    return
                time.sleep(ARR_VERIFIER_POLL_SECONDS)
        arr_verifier_failure(
            furthest_verified="NAS-backed import",
            blocker="Jellyfin drift",
            detail=f"Jellyfin could not query {candidate_title} ({candidate_year}) after the library refresh completed.",
        )


def reconcile_media_stack(master_ip: str, proxmox_host: str, kubeconfig: Path, kubectl: str) -> None:
    env = merged_env()
    require_env(["DOMAIN_NAME", "QUI_PASSWORD"], env)
    downloader_username = env.get("QBITTORRENT_USERNAME", "admin").strip() or "admin"
    downloader_password = env["QUI_PASSWORD"].strip()
    username, password, email = seerr_admin_identity(env)

    with cluster_session(proxmox_host, master_ip, kubeconfig, kubectl) as session_kubeconfig:
        bazarr_api_key = ""
        sabnzbd_api_key = ""
        radarr_api_key = ""
        sonarr_api_key = ""
        prowlarr_api_key = ""
        lidarr_api_key = ""
        radarr_root_folders: list[dict[str, object]] = []
        sonarr_root_folders: list[dict[str, object]] = []
        lidarr_root_folders: list[dict[str, object]] = []
        print("[stage] Media rollout gate")
        for resource in (
            "deployment/downloaders",
            "deployment/flaresolverr",
            "deployment/autobrr",
            "deployment/radarr",
            "deployment/sonarr",
            "deployment/prowlarr",
            "deployment/lidarr",
            "deployment/sabnzbd",
            "deployment/bazarr",
            "deployment/jellyfin",
            "statefulset/seerr",
        ):
            wait_for_rollout(kubectl, session_kubeconfig, namespace="media", resource=resource)
        print("[ok] Media rollout gate")

        radarr_api_key = read_arr_service_api_key(kubectl, session_kubeconfig, "radarr")
        sonarr_api_key = read_arr_service_api_key(kubectl, session_kubeconfig, "sonarr")
        prowlarr_api_key = read_arr_service_api_key(kubectl, session_kubeconfig, "prowlarr")
        lidarr_api_key = read_arr_service_api_key(kubectl, session_kubeconfig, "lidarr")
        sabnzbd_api_key = read_sabnzbd_service_api_key(kubectl, session_kubeconfig)

        print("[stage] Downloader bootstrap gate")
        try:
            bootstrap_downloaders_session(kubectl, session_kubeconfig, env)
        except HaaCError as exc:
            vpn_blocker = detect_vpn_blocker(kubectl, session_kubeconfig)
            if vpn_blocker:
                raise HaaCError(
                    "Downloader bootstrap is blocked by the ProtonVPN-backed downloader prerequisites.\n"
                    "Check the ProtonVPN OpenVPN credentials or subscription, then rerun `task media:post-install`.\n"
                    f"{vpn_blocker}"
                ) from exc
            raise
        print("[ok] Downloader bootstrap gate")

        print("[stage] Downloader preference gate")
        with kubectl_port_forward(kubectl, session_kubeconfig, "media", "svc/qbittorrent", 8080) as port:
            ensure_qbittorrent_app_preferences(
                port,
                username=downloader_username,
                password=downloader_password,
            )
            ensure_qbittorrent_category_paths(
                port,
                username=downloader_username,
                password=downloader_password,
            )
        print("[ok] Downloader preference gate")

        print("[stage] Media service probes")
        with kubectl_port_forward(kubectl, session_kubeconfig, "media", "svc/sabnzbd", 80) as port:
            ensure_sabnzbd_bootstrap(port, api_key=sabnzbd_api_key, domain_name=env["DOMAIN_NAME"])
        with kubectl_port_forward(kubectl, session_kubeconfig, "media", "svc/radarr", 80) as port:
            require_http_status(
                f"http://127.0.0.1:{port}/ping",
                label="Radarr /ping",
                expected_body_pattern=ARR_PING_SUCCESS_PATTERN,
            )
            ensure_media_storage_path(
                kubectl,
                session_kubeconfig,
                container_name="radarr",
                path=ARR_DEFAULT_ROOT_FOLDERS["radarr"],
            )
            radarr_root_folders = ensure_arr_root_folder(
                port,
                app_name="Radarr",
                api_key=radarr_api_key,
                path=ARR_DEFAULT_ROOT_FOLDERS["radarr"],
            )
            ensure_arr_qbittorrent_download_client(
                port,
                app_name="Radarr",
                api_key=radarr_api_key,
                username=downloader_username,
                password=downloader_password,
            )
            ensure_arr_sabnzbd_download_client(
                port,
                app_name="Radarr",
                api_key=radarr_api_key,
                sabnzbd_api_key=sabnzbd_api_key,
            )
            ensure_arr_common_settings(port, app_name="Radarr", api_key=radarr_api_key)
        with kubectl_port_forward(kubectl, session_kubeconfig, "media", "svc/sonarr", 80) as port:
            require_http_status(
                f"http://127.0.0.1:{port}/ping",
                label="Sonarr /ping",
                expected_body_pattern=ARR_PING_SUCCESS_PATTERN,
            )
            ensure_media_storage_path(
                kubectl,
                session_kubeconfig,
                container_name="sonarr",
                path=ARR_DEFAULT_ROOT_FOLDERS["sonarr"],
            )
            sonarr_root_folders = ensure_arr_root_folder(
                port,
                app_name="Sonarr",
                api_key=sonarr_api_key,
                path=ARR_DEFAULT_ROOT_FOLDERS["sonarr"],
            )
            ensure_arr_qbittorrent_download_client(
                port,
                app_name="Sonarr",
                api_key=sonarr_api_key,
                username=downloader_username,
                password=downloader_password,
            )
            ensure_arr_sabnzbd_download_client(
                port,
                app_name="Sonarr",
                api_key=sonarr_api_key,
                sabnzbd_api_key=sabnzbd_api_key,
            )
            ensure_arr_common_settings(port, app_name="Sonarr", api_key=sonarr_api_key)
        with kubectl_port_forward(kubectl, session_kubeconfig, "media", "svc/lidarr", 80) as port:
            require_http_status(
                f"http://127.0.0.1:{port}/ping",
                label="Lidarr /ping",
                expected_body_pattern=ARR_PING_SUCCESS_PATTERN,
            )
            ensure_media_storage_path(
                kubectl,
                session_kubeconfig,
                container_name="lidarr",
                path=ARR_DEFAULT_ROOT_FOLDERS["lidarr"],
            )
            lidarr_root_folders = ensure_arr_root_folder(
                port,
                app_name="Lidarr",
                api_key=lidarr_api_key,
                path=ARR_DEFAULT_ROOT_FOLDERS["lidarr"],
                api_version="v1",
            )
            ensure_arr_qbittorrent_download_client(
                port,
                app_name="Lidarr",
                api_key=lidarr_api_key,
                username=downloader_username,
                password=downloader_password,
                api_version="v1",
            )
            ensure_arr_sabnzbd_download_client(
                port,
                app_name="Lidarr",
                api_key=lidarr_api_key,
                sabnzbd_api_key=sabnzbd_api_key,
                api_version="v1",
            )
            ensure_arr_common_settings(port, app_name="Lidarr", api_key=lidarr_api_key, api_version="v1")
        whisparr_api_key = read_arr_service_api_key(kubectl, session_kubeconfig, "whisparr")
        with kubectl_port_forward(kubectl, session_kubeconfig, "media", "svc/whisparr", 80) as port:
            require_http_status(
                f"http://127.0.0.1:{port}/ping",
                label="Whisparr /ping",
                expected_body_pattern=ARR_PING_SUCCESS_PATTERN,
            )
            ensure_media_storage_path(
                kubectl,
                session_kubeconfig,
                container_name="whisparr",
                path=ARR_DEFAULT_ROOT_FOLDERS["whisparr"],
            )
            ensure_arr_root_folder(
                port,
                app_name="Whisparr",
                api_key=whisparr_api_key,
                path=ARR_DEFAULT_ROOT_FOLDERS["whisparr"],
            )
            ensure_arr_qbittorrent_download_client(
                port,
                app_name="Whisparr",
                api_key=whisparr_api_key,
                username=downloader_username,
                password=downloader_password,
            )
            ensure_arr_sabnzbd_download_client(
                port,
                app_name="Whisparr",
                api_key=whisparr_api_key,
                sabnzbd_api_key=sabnzbd_api_key,
            )
            ensure_arr_common_settings(port, app_name="Whisparr", api_key=whisparr_api_key)
        with kubectl_port_forward(kubectl, session_kubeconfig, "media", "svc/prowlarr", 80) as port:
            require_http_status(
                f"http://127.0.0.1:{port}/ping",
                label="Prowlarr /ping",
                expected_body_pattern=ARR_PING_SUCCESS_PATTERN,
            )
            ensure_prowlarr_qbittorrent_download_client(
                port,
                api_key=prowlarr_api_key,
                username=downloader_username,
                password=downloader_password,
            )
            ensure_prowlarr_sabnzbd_download_client(
                port,
                api_key=prowlarr_api_key,
                sabnzbd_api_key=sabnzbd_api_key,
            )
            ensure_prowlarr_application(
                port,
                api_key=prowlarr_api_key,
                implementation="Radarr",
                downstream_api_key=radarr_api_key,
                downstream_url=RADARR_INTERNAL_URL,
            )
            ensure_prowlarr_application(
                port,
                api_key=prowlarr_api_key,
                implementation="Sonarr",
                downstream_api_key=sonarr_api_key,
                downstream_url=SONARR_INTERNAL_URL,
            )
            ensure_prowlarr_application(
                port,
                api_key=prowlarr_api_key,
                implementation="Lidarr",
                downstream_api_key=lidarr_api_key,
                downstream_url=LIDARR_INTERNAL_URL,
            )
            ensure_prowlarr_application(
                port,
                api_key=prowlarr_api_key,
                implementation="Whisparr",
                downstream_api_key=whisparr_api_key,
                downstream_url=WHISPARR_INTERNAL_URL,
            )
        bazarr_api_key = read_bazarr_service_api_key(kubectl, session_kubeconfig)
        with kubectl_port_forward(kubectl, session_kubeconfig, "media", "svc/bazarr", 80) as port:
            require_http_status(
                f"http://127.0.0.1:{port}/login",
                label="Bazarr /login",
                expected_statuses=(200, 302),
            )
            ensure_bazarr_bootstrap(
                port,
                env=env,
                api_key=bazarr_api_key,
                radarr_api_key=radarr_api_key,
                sonarr_api_key=sonarr_api_key,
            )
        ensure_recyclarr_runtime_secret(
            kubectl,
            session_kubeconfig,
            radarr_api_key=radarr_api_key,
            sonarr_api_key=sonarr_api_key,
            lidarr_api_key=lidarr_api_key,
            whisparr_api_key=whisparr_api_key,
            bazarr_api_key=bazarr_api_key,
            sabnzbd_api_key=sabnzbd_api_key,
        )
        for resource in ("deployment/lidarr", "deployment/whisparr", "deployment/sabnzbd", "deployment/bazarr-exportarr", "deployment/unpackerr"):
            run(
                [
                    kubectl,
                    "--kubeconfig",
                    str(session_kubeconfig),
                    "-n",
                    "media",
                    "rollout",
                    "restart",
                    resource,
                ],
                check=False,
                capture_output=True,
            )
            wait_for_rollout(kubectl, session_kubeconfig, namespace="media", resource=resource)
        with kubectl_port_forward(kubectl, session_kubeconfig, "media", "svc/jellyfin", 80) as port:
            require_http_status(f"http://127.0.0.1:{port}/health", label="Jellyfin /health")
            if jellyfin_startup_incomplete(jellyfin_public_info(port)):
                ensure_jellyfin_admin_ready(port, username=username, password=password, domain_name=env["DOMAIN_NAME"])
            jellyfin_auth = authenticate_jellyfin_admin(port, username=username, password=password)
            ensure_jellyfin_system_configuration(port, access_token=str(jellyfin_auth["AccessToken"]))
            ensure_jellyfin_libraries(port, access_token=str(jellyfin_auth["AccessToken"]))
        with kubectl_port_forward(kubectl, session_kubeconfig, "media", "svc/seerr", 80) as port:
            public_settings = seerr_public_settings(port)
            opener = seerr_login_with_jellyfin(
                port,
                username=username,
                password=password,
                email=email,
                public_settings=public_settings,
            )
            ensure_seerr_main_settings(opener, port, domain_name=env["DOMAIN_NAME"])
            jellyfin_settings = ensure_seerr_jellyfin_settings(opener, port, domain_name=env["DOMAIN_NAME"])
            libraries = json_array(jellyfin_settings.get("libraries") if isinstance(jellyfin_settings, dict) else [])
            if not any(bool(item.get("enabled")) for item in libraries):
                raise HaaCError("Seerr reached Jellyfin, but Jellyfin still exposes no enabled libraries for discovery.")
            ensure_seerr_radarr_settings(
                opener,
                port,
                domain_name=env["DOMAIN_NAME"],
                radarr_api_key=radarr_api_key,
                fallback_root_folders=radarr_root_folders,
            )
            ensure_seerr_sonarr_settings(
                opener,
                port,
                domain_name=env["DOMAIN_NAME"],
                sonarr_api_key=sonarr_api_key,
                fallback_root_folders=sonarr_root_folders,
            )
            if not bool(public_settings.get("initialized")):
                initialized = http_request_json(
                    f"http://127.0.0.1:{port}/api/v1/settings/initialize",
                    method="POST",
                    opener=opener,
                )
                if not isinstance(initialized, dict) or not bool(initialized.get("initialized")):
                    raise HaaCError("Seerr did not finish initialization after the service bootstrap completed.")
            final_public_settings = seerr_public_settings(port)
            if not bool(final_public_settings.get("initialized")):
                raise HaaCError("Seerr settings surface is still not initialized after media reconciliation.")
        print("[ok] Media service probes")

        print("[stage] Media quality policy")
        ensure_recyclarr_runtime_secret(
            kubectl,
            session_kubeconfig,
            radarr_api_key=radarr_api_key,
            sonarr_api_key=sonarr_api_key,
            lidarr_api_key=lidarr_api_key,
            bazarr_api_key=bazarr_api_key,
            sabnzbd_api_key=sabnzbd_api_key,
        )
        run_recyclarr_sync_job(kubectl, session_kubeconfig)
        with kubectl_port_forward(kubectl, session_kubeconfig, "media", "svc/radarr", 80) as port:
            verify_recyclarr_sync_surface(
                port,
                app_name="Radarr",
                api_key=radarr_api_key,
                expected_profile="HD Bluray + WEB",
            )
            ensure_arr_language_preferences(
                port,
                app_name="Radarr",
                api_key=radarr_api_key,
                preferred_languages=desired_arr_language_preferences(env),
            )
        with kubectl_port_forward(kubectl, session_kubeconfig, "media", "svc/sonarr", 80) as port:
            verify_recyclarr_sync_surface(
                port,
                app_name="Sonarr",
                api_key=sonarr_api_key,
                expected_profile="WEB-1080p",
            )
            ensure_arr_language_preferences(
                port,
                app_name="Sonarr",
                api_key=sonarr_api_key,
                preferred_languages=desired_arr_language_preferences(env),
            )
        print("[ok] Media quality policy")

        print("[stage] Media metrics warmup")
        warm_flaresolverr_metrics(kubectl, session_kubeconfig)
        verify_media_metrics_surface(kubectl, session_kubeconfig)
        print("[ok] Media metrics warmup")


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


def prune_empty_dirs(root: Path, *, keep_root: bool = True) -> list[str]:
    if not root.exists():
        return []
    removed: list[str] = []
    directories = sorted((path for path in root.rglob("*") if path.is_dir()), key=lambda path: len(path.parts), reverse=True)
    for path in directories:
        try:
            path.rmdir()
        except OSError:
            continue
        removed.append(str(path.relative_to(ROOT)))
    if not keep_root:
        try:
            root.rmdir()
        except OSError:
            return removed
        removed.append(str(root.relative_to(ROOT)))
    return removed


def clean_local_artifacts() -> None:
    removed: list[str] = []
    skipped: list[str] = []
    for artifact_dir in LEGACY_ARTIFACT_DIRS:
        if artifact_dir.exists():
            relative_dir = str(artifact_dir.relative_to(ROOT))
            if gitstatelib.git_tracked_paths_under(ROOT, relative_dir):
                skipped.append(relative_dir)
                continue
            shutil.rmtree(artifact_dir, ignore_errors=True)
            removed.append(relative_dir)

    for pattern in LEGACY_ARTIFACT_PATTERNS:
        for path in ROOT.glob(pattern):
            if path.is_file():
                path.unlink(missing_ok=True)
                removed.append(str(path.relative_to(ROOT)))

    for scratch_root in SANCTIONED_SCRATCH_ROOTS:
        removed.extend(prune_empty_dirs(scratch_root, keep_root=True))

    if removed:
        print("[ok] Removed local investigation artifacts:")
        for item in sorted(removed):
            print(f"  - {item}")
    else:
        print("[ok] No stray local investigation artifacts were found outside .tmp/")
    if skipped:
        print("[warn] Skipped tracked legacy artifact paths; remove them with a dedicated Git cleanup instead:")
        for item in sorted(skipped):
            print(f"  - {item}")


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
    require_env(
        [
            "AUTHELIA_ADMIN_PASSWORD",
            "GRAFANA_ADMIN_PASSWORD",
            "LITMUS_ADMIN_PASSWORD",
            "LITMUS_MONGODB_ROOT_PASSWORD",
            "LITMUS_MONGODB_REPLICA_SET_KEY",
            "SEMAPHORE_ADMIN_PASSWORD",
            "QUI_PASSWORD",
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
    warn_shared_credential_scope(env)


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
        "lxc_master_memory": "LXC_MASTER_MEMORY",
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


def cmd_repair_node_identity_drift(args: argparse.Namespace) -> None:
    env = merged_env()
    ensure_repo_ssh_keypair()
    proxmox_host = args.proxmox_host or proxmox_access_host(env)
    quarantine_duplicate_k3s_lxc_identities(proxmox_host, ROOT / args.tofu_dir, env=env)


def cmd_run_ansible(args: argparse.Namespace) -> None:
    env = merged_env()
    ensure_repo_ssh_keypair()
    ensure_semaphore_ssh_keypair()
    quarantine_duplicate_k3s_lxc_identities(proxmox_access_host(env), ROOT / "tofu", env=env)
    refresh_cluster_known_hosts(env)
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


def cmd_cleanup_security_signal_residue(args: argparse.Namespace) -> None:
    cleanup_security_signal_residue(args.master_ip, args.proxmox_host, Path(args.kubeconfig), args.kubectl)


def cmd_clear_crowdsec_operator_ban(args: argparse.Namespace) -> None:
    cleared = clear_current_operator_crowdsec_probe_ban(
        args.master_ip,
        args.proxmox_host,
        Path(args.kubeconfig),
        args.kubectl,
    )
    if cleared:
        print("[ok] Cleared temporary CrowdSec false-positive bans for the current operator IP.")
    else:
        print("[ok] No temporary CrowdSec false-positive ban was active for the current operator IP.")


def cmd_verify_web(args: argparse.Namespace) -> None:
    verify_web(
        args.domain,
        master_ip=args.master_ip,
        proxmox_host=args.proxmox_host,
        kubeconfig=Path(args.kubeconfig) if args.kubeconfig else None,
        kubectl=args.kubectl or "kubectl",
    )


def cmd_sync_cloudflare(args: argparse.Namespace) -> None:
    sync_cloudflare()
    if args.master_ip and args.proxmox_host and args.kubeconfig and args.kubectl:
        restart_cloudflared_rollout(args.master_ip, args.proxmox_host, Path(args.kubeconfig), args.kubectl)


def cmd_configure_apps(args: argparse.Namespace) -> None:
    bootstrap_downloaders(args.master_ip, args.proxmox_host, Path(args.kubeconfig), args.kubectl)


def cmd_reconcile_media_stack(args: argparse.Namespace) -> None:
    reconcile_media_stack(args.master_ip, args.proxmox_host, Path(args.kubeconfig), args.kubectl)


def cmd_verify_arr_flow(args: argparse.Namespace) -> None:
    verify_arr_flow(
        args.master_ip,
        args.proxmox_host,
        Path(args.kubeconfig),
        args.kubectl,
        timeout_seconds=args.timeout,
    )


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

    command = subparsers.add_parser("repair-node-identity-drift")
    command.add_argument("--proxmox-host")
    command.add_argument("--tofu-dir", default="tofu")
    command.set_defaults(func=cmd_repair_node_identity_drift)

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

    command = subparsers.add_parser("cleanup-security-signal-residue")
    command.add_argument("--master-ip", required=True)
    command.add_argument("--proxmox-host", required=True)
    command.add_argument("--kubeconfig", required=True)
    command.add_argument("--kubectl", default="kubectl")
    command.set_defaults(func=cmd_cleanup_security_signal_residue)

    command = subparsers.add_parser("clear-crowdsec-operator-ban")
    command.add_argument("--master-ip", required=True)
    command.add_argument("--proxmox-host", required=True)
    command.add_argument("--kubeconfig", required=True)
    command.add_argument("--kubectl", default="kubectl")
    command.set_defaults(func=cmd_clear_crowdsec_operator_ban)

    command = subparsers.add_parser("verify-web")
    command.add_argument("--domain", required=True)
    command.add_argument("--master-ip")
    command.add_argument("--proxmox-host")
    command.add_argument("--kubeconfig")
    command.add_argument("--kubectl")
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

    command = subparsers.add_parser("reconcile-media-stack")
    command.add_argument("--master-ip", required=True)
    command.add_argument("--proxmox-host", required=True)
    command.add_argument("--kubeconfig", required=True)
    command.add_argument("--kubectl", default="kubectl")
    command.set_defaults(func=cmd_reconcile_media_stack)

    command = subparsers.add_parser("verify-arr-flow")
    command.add_argument("--master-ip", required=True)
    command.add_argument("--proxmox-host", required=True)
    command.add_argument("--kubeconfig", required=True)
    command.add_argument("--kubectl", default="kubectl")
    command.add_argument("--timeout", type=int, default=1800)
    command.set_defaults(func=cmd_verify_arr_flow)

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
