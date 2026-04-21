from __future__ import annotations

import contextlib
import importlib.util
import io
import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
HAAC_PATH = ROOT / "scripts" / "haac.py"
HAAC_SPEC = importlib.util.spec_from_file_location("haac_module", HAAC_PATH)
haac = importlib.util.module_from_spec(HAAC_SPEC)
assert HAAC_SPEC.loader is not None
HAAC_SPEC.loader.exec_module(haac)


class MergedEnvTests(unittest.TestCase):
    def test_lxc_password_falls_back_to_proxmox_host_password(self) -> None:
        with mock.patch.object(haac, "load_env_file", return_value={"LXC_PASSWORD": "demo-secret"}):
            with mock.patch.dict(os.environ, {}, clear=True):
                merged = haac.merged_env()

        self.assertEqual(merged["LXC_PASSWORD"], "demo-secret")
        self.assertEqual(merged["PROXMOX_HOST_PASSWORD"], "demo-secret")

    def test_explicit_proxmox_host_password_override_wins(self) -> None:
        with mock.patch.object(haac, "load_env_file", return_value={"LXC_PASSWORD": "demo-secret"}):
            with mock.patch.dict(os.environ, {"PROXMOX_HOST_PASSWORD": "explicit-secret"}, clear=True):
                merged = haac.merged_env()

        self.assertEqual(merged["LXC_PASSWORD"], "demo-secret")
        self.assertEqual(merged["PROXMOX_HOST_PASSWORD"], "explicit-secret")

    def test_qui_password_derives_qbittorrent_hash_and_secret_checksums(self) -> None:
        with mock.patch.object(
            haac,
            "load_env_file",
            return_value={"QUI_PASSWORD": "demo-secret", "GRAFANA_ADMIN_PASSWORD": "grafana-secret"},
        ):
            with mock.patch.dict(os.environ, {}, clear=True):
                merged = haac.merged_env()

        self.assertTrue(merged["QBITTORRENT_PASSWORD_PBKDF2"].startswith("@ByteArray("))
        self.assertEqual(
            merged["QBITTORRENT_PASSWORD_PBKDF2"],
            haac.qbittorrent_password_pbkdf2("demo-secret"),
        )
        self.assertIn("DOWNLOADERS_AUTH_SECRET_SHA256", merged)
        self.assertIn("HOMEPAGE_WIDGETS_SECRET_SHA256", merged)

    def test_protonvpn_credentials_derive_repo_managed_secret_checksum(self) -> None:
        with mock.patch.object(
            haac,
            "load_env_file",
            return_value={"PROTONVPN_OPENVPN_USERNAME": "demo-user+pmp+nr", "PROTONVPN_OPENVPN_PASSWORD": "secret"},
        ):
            with mock.patch.dict(os.environ, {}, clear=True):
                merged = haac.merged_env()

        self.assertEqual(
            merged["PROTONVPN_SECRET_SHA256"],
            haac.stable_secret_checksum(
                {
                    "OPENVPN_USER": "demo-user+pmp",
                    "OPENVPN_PASSWORD": "secret",
                }
            ),
        )

    def test_main_identity_derives_supported_login_defaults(self) -> None:
        with mock.patch.object(
            haac,
            "load_env_file",
            return_value={
                "DOMAIN_NAME": "example.com",
                "HAAC_MAIN_USERNAME": "haacadmin",
                "HAAC_MAIN_PASSWORD": "demo-secret",
                "HAAC_MAIN_EMAIL": "ops@example.com",
                "HAAC_MAIN_NAME": "Ops Admin",
            },
        ):
            with mock.patch.dict(os.environ, {}, clear=True):
                merged = haac.merged_env()

        self.assertEqual(merged["AUTHELIA_ADMIN_USERNAME"], "haacadmin")
        self.assertEqual(merged["AUTHELIA_ADMIN_PASSWORD"], "demo-secret")
        self.assertEqual(merged["ARGOCD_USERNAME"], "haacadmin")
        self.assertEqual(merged["ARGOCD_PASSWORD"], "demo-secret")
        self.assertEqual(merged["GRAFANA_ADMIN_USERNAME"], "haacadmin")
        self.assertEqual(merged["SEMAPHORE_ADMIN_USERNAME"], "haacadmin")
        self.assertEqual(merged["LITMUS_ADMIN_USERNAME"], "haacadmin")
        self.assertEqual(merged["JELLYFIN_ADMIN_USERNAME"], "haacadmin")
        self.assertEqual(merged["JELLYFIN_ADMIN_PASSWORD"], "demo-secret")
        self.assertEqual(merged["JELLYFIN_ADMIN_EMAIL"], "ops@example.com")
        self.assertNotIn("QBITTORRENT_USERNAME", merged)
        self.assertNotIn("QUI_PASSWORD", merged)
        self.assertEqual(merged["SEMAPHORE_ADMIN_EMAIL"], "ops@example.com")
        self.assertEqual(merged["SEMAPHORE_ADMIN_NAME"], "Ops Admin")

    def test_shared_downloader_flag_derives_qbit_and_qui_from_main(self) -> None:
        with mock.patch.object(
            haac,
            "load_env_file",
            return_value={
                "HAAC_MAIN_USERNAME": "haacadmin",
                "HAAC_MAIN_PASSWORD": "demo-secret",
                "HAAC_ENABLE_SHARED_DOWNLOADER_CREDENTIALS": "true",
            },
        ):
            with mock.patch.dict(os.environ, {}, clear=True):
                merged = haac.merged_env()

        self.assertEqual(merged["QBITTORRENT_USERNAME"], "haacadmin")
        self.assertEqual(merged["QUI_PASSWORD"], "demo-secret")

    def test_protonvpn_port_forward_username_appends_pmp_and_strips_legacy_nr_suffix(self) -> None:
        self.assertEqual(haac.protonvpn_port_forward_username("demo-user"), "demo-user+pmp")
        self.assertEqual(haac.protonvpn_port_forward_username("demo-user+pmp"), "demo-user+pmp")
        self.assertEqual(haac.protonvpn_port_forward_username("demo-user+pmp+nr"), "demo-user+pmp")
        self.assertEqual(haac.protonvpn_port_forward_username("demo-user+f2"), "demo-user+f2+pmp")

    def test_authelia_admin_password_seeds_other_control_plane_passwords(self) -> None:
        with mock.patch.object(
            haac,
            "load_env_file",
            return_value={
                "AUTHELIA_ADMIN_USERNAME": "opsadmin",
                "AUTHELIA_ADMIN_PASSWORD": "demo-secret",
            },
        ):
            with mock.patch.dict(os.environ, {}, clear=True):
                merged = haac.merged_env()

        self.assertEqual(merged["GRAFANA_ADMIN_PASSWORD"], "demo-secret")
        self.assertEqual(merged["SEMAPHORE_ADMIN_PASSWORD"], "demo-secret")
        self.assertEqual(merged["LITMUS_ADMIN_PASSWORD"], "demo-secret")

    def test_service_specific_identity_overrides_win_over_main_defaults_even_if_blank(self) -> None:
        with mock.patch.object(
            haac,
            "load_env_file",
            return_value={
                "DOMAIN_NAME": "example.com",
                "HAAC_MAIN_USERNAME": "haacadmin",
                "HAAC_MAIN_PASSWORD": "demo-secret",
                "GRAFANA_ADMIN_USERNAME": "",
                "GRAFANA_ADMIN_PASSWORD": "grafana-secret",
                "SEMAPHORE_ADMIN_USERNAME": "semaphore-admin",
            },
        ):
            with mock.patch.dict(os.environ, {}, clear=True):
                merged = haac.merged_env()

        self.assertEqual(merged["GRAFANA_ADMIN_USERNAME"], "haacadmin")
        self.assertEqual(merged["GRAFANA_ADMIN_PASSWORD"], "grafana-secret")
        self.assertEqual(merged["SEMAPHORE_ADMIN_USERNAME"], "semaphore-admin")

    def test_traefik_trusted_ips_default_and_crowdsec_checksum_are_derived(self) -> None:
        with mock.patch.object(
            haac,
            "load_env_file",
            return_value={
                "CROWDSEC_BOUNCER_KEY": "crowdsec-secret-key",
            },
        ):
            with mock.patch.dict(os.environ, {}, clear=True):
                merged = haac.merged_env()

        self.assertIn("TRAEFIK_TRUSTED_IPS", merged)
        self.assertIn("103.21.244.0/22", merged["TRAEFIK_TRUSTED_IPS"])
        self.assertIn("CROWDSEC_TRAEFIK_SECRET_SHA256", merged)

    def test_invalid_identity_username_raises(self) -> None:
        with mock.patch.object(
            haac,
            "load_env_file",
            return_value={
                "HAAC_MAIN_USERNAME": "bad user",
                "HAAC_MAIN_PASSWORD": "demo-secret",
            },
        ):
            with mock.patch.dict(os.environ, {}, clear=True):
                with self.assertRaisesRegex(ValueError, "unsupported characters"):
                    haac.merged_env()

    def test_resolved_master_ip_prefers_env_and_strips_cidr(self) -> None:
        with mock.patch.object(haac, "merged_env", return_value={"K3S_MASTER_IP": "192.168.0.211/24"}):
            self.assertEqual(haac.resolved_master_ip_value(), "192.168.0.211")

    def test_effective_master_ip_argument_recovers_from_loopback_default(self) -> None:
        with mock.patch.object(haac, "merged_env", return_value={"K3S_MASTER_IP": "192.168.0.211/24"}):
            self.assertEqual(haac.effective_master_ip_argument("127.0.0.1"), "192.168.0.211")
            self.assertEqual(haac.effective_master_ip_argument("192.168.0.212"), "192.168.0.212")


class QbittorrentPasswordHashTests(unittest.TestCase):
    def test_qbittorrent_password_pbkdf2_is_deterministic(self) -> None:
        first = haac.qbittorrent_password_pbkdf2("MySecretPassword123!")
        second = haac.qbittorrent_password_pbkdf2("MySecretPassword123!")
        third = haac.qbittorrent_password_pbkdf2("different-secret")

        self.assertEqual(first, second)
        self.assertNotEqual(first, third)
        self.assertRegex(first, r"^@ByteArray\([A-Za-z0-9+/=]+:[A-Za-z0-9+/=]+\)$")


class SshTunnelRetryTests(unittest.TestCase):
    def test_windows_retries_rebuild_tunnel_command_after_cleanup(self) -> None:
        popen_instances = []

        class FailedProcess:
            def __init__(self, command: list[str]) -> None:
                self.command = command
                self.stderr = io.StringIO("permission denied")
                self.pid = 12345
                popen_instances.append(self)

            def poll(self) -> int:
                return 1

        built_commands: list[list[str]] = []

        def fake_tunnel_command(*args, **kwargs):
            command = [f"retry-{len(built_commands) + 1}"]
            built_commands.append(command)
            return command

        with mock.patch.object(haac, "allocate_local_port", return_value=16443):
            with mock.patch.object(haac, "merged_env", return_value={"HAAC_WSL_DISTRO": "Debian"}):
                with mock.patch.object(haac, "is_windows", return_value=True):
                    with mock.patch.object(haac, "proxmox_tunnel_command", side_effect=fake_tunnel_command):
                        with mock.patch.object(haac.subprocess, "Popen", side_effect=lambda *a, **k: FailedProcess(a[0])):
                            with mock.patch.object(haac, "cleanup_wsl_runtime") as cleanup_runtime:
                                with mock.patch.object(haac.time, "sleep"):
                                    with self.assertRaises(haac.HaaCError) as ctx:
                                        with haac.ssh_tunnel("192.168.0.200", "192.168.0.211"):
                                            self.fail("ssh_tunnel should not yield on repeated failures")

        self.assertEqual(len(built_commands), 3)
        self.assertEqual([instance.command for instance in popen_instances], built_commands)
        self.assertEqual(cleanup_runtime.call_count, 3)
        self.assertIn("permission denied", str(ctx.exception))

    def test_wsl_runtime_dir_is_scoped_per_process_and_thread(self) -> None:
        env = {"HAAC_WSL_DISTRO": "Debian"}

        with mock.patch.object(haac.os, "getpid", return_value=4242):
            with mock.patch.object(haac.threading, "get_ident", return_value=99):
                runtime_dir = haac.wsl_runtime_dir(env)

        self.assertEqual(runtime_dir, "/tmp/haac-runtime/Debian/pid-4242-tid-99")


class TaskRunStreamingTests(unittest.TestCase):
    def test_task_run_streams_with_utf8_replace(self) -> None:
        observed_kwargs: dict[str, object] = {}

        class FakeStream:
            def __iter__(self):
                yield "TASK: one\n"
                yield "TASK: two\n"

        class FakeProcess:
            stdout = FakeStream()

            def wait(self) -> int:
                return 0

        def fake_popen(*args, **kwargs):
            observed_kwargs.update(kwargs)
            return FakeProcess()

        with mock.patch.object(haac.subprocess, "Popen", side_effect=fake_popen):
            with mock.patch("builtins.print") as fake_print:
                returncode, output_lines = haac.run_task_with_output("task", ["up"], {})

        self.assertEqual(returncode, 0)
        self.assertEqual(output_lines, ["TASK: one", "TASK: two"])
        self.assertEqual(observed_kwargs["encoding"], "utf-8")
        self.assertEqual(observed_kwargs["errors"], "replace")
        fake_print.assert_any_call("TASK: one\n", end="")
        fake_print.assert_any_call("TASK: two\n", end="")


class UpFailureSummaryTests(unittest.TestCase):
    def test_emit_up_failure_summary_preserves_explicit_recovery_lines(self) -> None:
        lines = [
            "task: [configure-os] python scripts/haac.py run-ansible",
            "[recovery] Failing phase: GitOps readiness",
            "[recovery] Last verified phase: GitOps publication",
            "[recovery] Full rerun guidance: Retry GitOps post-install after fixing the failing app.",
        ]

        with mock.patch("builtins.print") as fake_print:
            haac.emit_up_failure_summary(lines)

        fake_print.assert_any_call("[recovery] Failing phase: GitOps readiness", file=haac.sys.stderr)
        fake_print.assert_any_call("[recovery] Last verified phase: GitOps publication", file=haac.sys.stderr)
        fake_print.assert_any_call(
            "[recovery] Full rerun guidance: Retry GitOps post-install after fixing the failing app.",
            file=haac.sys.stderr,
        )

    def test_emit_up_failure_summary_handles_nested_gitops_tasks_monotonically(self) -> None:
        lines = [
            "task: [preflight] task: check-env",
            "task: [configure-os] python scripts/haac.py run-ansible",
            "task: [internal:push-changes] python scripts/haac.py push-changes",
            "task: [internal:wait-for-argocd-sync] python scripts/haac.py wait-for-stack",
            "task: [security:post-install] python scripts/haac.py run-ansible --playbook ansible/maintenance-security-playbook.yml",
            "task: [check-env] python scripts/haac.py check-env",
            "task: [chaos:post-install] python scripts/haac.py reconcile-litmus-chaos",
        ]

        with mock.patch("builtins.print") as fake_print:
            haac.emit_up_failure_summary(lines)

        fake_print.assert_any_call("[recovery] Failing phase: GitOps readiness", file=haac.sys.stderr)
        fake_print.assert_any_call("[recovery] Last verified phase: GitOps publication", file=haac.sys.stderr)


class KnownHostsRefreshTests(unittest.TestCase):
    def test_worker_nodes_config_preserves_declared_keys(self) -> None:
        env = {
            "WORKER_NODES_JSON": json.dumps(
                {
                    "worker1": {"hostname": "haacarr-worker1", "ip": "192.168.0.212/24"},
                    "worker2": {"hostname": "haacarr-worker2", "ip": "192.168.0.213"},
                }
            )
        }

        self.assertEqual(
            haac.worker_nodes_config(env),
            [
                ("worker1", {"hostname": "haacarr-worker1", "ip": "192.168.0.212/24"}),
                ("worker2", {"hostname": "haacarr-worker2", "ip": "192.168.0.213"}),
            ],
        )

    def test_cluster_node_hosts_strips_cidr_and_preserves_worker_order(self) -> None:
        env = {
            "K3S_MASTER_IP": "192.168.0.211/24",
            "WORKER_NODES_JSON": json.dumps(
                {
                    "worker1": {"hostname": "haacarr-worker1", "ip": "192.168.0.212/24"},
                    "worker2": {"hostname": "haacarr-worker2", "ip": "192.168.0.213"},
                }
            ),
        }

        self.assertEqual(
            haac.cluster_node_hosts(env),
            ["192.168.0.211", "192.168.0.212", "192.168.0.213"],
        )

    def test_replace_known_host_entries_replaces_matching_host_and_keeps_others(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "known_hosts"
            path.write_text(
                "192.168.0.211 ssh-ed25519 OLDMASTER\n"
                "192.168.0.212 ssh-ed25519 WORKER\n",
                encoding="utf-8",
            )

            haac.replace_known_host_entries(
                path,
                "192.168.0.211",
                "192.168.0.211 ssh-ed25519 NEWMASTER\n",
            )

            self.assertEqual(
                path.read_text(encoding="utf-8"),
                "192.168.0.212 ssh-ed25519 WORKER\n"
                "192.168.0.211 ssh-ed25519 NEWMASTER\n",
            )


class NodeIdentityDriftTests(unittest.TestCase):
    def test_proxmox_lxc_ipv4_extracts_static_ip(self) -> None:
        config = {
            "net0": "name=eth0,bridge=vmbr0,gw=192.168.0.1,ip=192.168.0.212/24,type=veth",
            "hostname": "haacarr-worker1",
        }

        self.assertEqual(haac.proxmox_lxc_ipv4(config), "192.168.0.212")

    def test_find_duplicate_k3s_lxc_identities_selects_only_unmanaged_collisions(self) -> None:
        env = {
            "LXC_MASTER_HOSTNAME": "haacarr-master",
            "K3S_MASTER_IP": "192.168.0.211/24",
            "WORKER_NODES_JSON": json.dumps(
                {
                    "worker1": {"hostname": "haacarr-worker1", "ip": "192.168.0.212/24"},
                    "worker2": {"hostname": "haacarr-worker2", "ip": "192.168.0.213/24"},
                }
            ),
        }
        tofu_outputs = {
            "master_vmid": {"value": 100},
            "workers": {
                "value": {
                    "worker1": {"vmid": 102, "ip": "192.168.0.212"},
                    "worker2": {"vmid": 101, "ip": "192.168.0.213"},
                }
            },
        }
        resources = [
            {"vmid": "100", "node": "pve", "name": "haacarr-master", "status": "running"},
            {"vmid": "101", "node": "pve", "name": "haacarr-worker2", "status": "running"},
            {"vmid": "102", "node": "pve", "name": "haacarr-worker1", "status": "running"},
            {"vmid": "104", "node": "pve", "name": "haacarr-worker2", "status": "running"},
            {"vmid": "105", "node": "pve", "name": "haacarr-worker1", "status": "running"},
            {"vmid": "103", "node": "pve", "name": "satisfactory", "status": "stopped"},
        ]
        configs = {
            ("pve", "104"): {"hostname": "haacarr-worker2", "net0": "name=eth0,ip=192.168.0.250/24"},
            ("pve", "105"): {"hostname": "other-host", "net0": "name=eth0,ip=192.168.0.212/24"},
            ("pve", "103"): {"hostname": "satisfactory", "net0": "name=eth0,ip=192.168.0.240/24"},
        }

        with mock.patch.object(haac, "tofu_output_json", return_value=tofu_outputs):
            with mock.patch.object(haac, "proxmox_lxc_resources", return_value=resources):
                with mock.patch.object(
                    haac,
                    "proxmox_lxc_config",
                    side_effect=lambda host, node, vmid: configs[(node, vmid)],
                ):
                    duplicates = haac.find_duplicate_k3s_lxc_identities("192.168.0.200", Path("tofu"), env=env)

        self.assertEqual([item["vmid"] for item in duplicates], ["104", "105"])
        self.assertEqual(duplicates[0]["reasons"], ["hostname haacarr-worker2"])
        self.assertEqual(duplicates[1]["reasons"], ["IPv4 192.168.0.212"])

    def test_quarantine_duplicate_k3s_lxc_identities_disables_onboot_and_stops_duplicates(self) -> None:
        duplicates = [
            {"vmid": "104", "hostname": "haacarr-worker2", "status": "running", "reasons": ["hostname haacarr-worker2"]},
            {"vmid": "105", "hostname": "haacarr-worker1", "status": "stopped", "reasons": ["IPv4 192.168.0.212"]},
        ]
        status_responses = {
            "104": ["status: running", "status: stopped"],
            "105": ["status: stopped"],
        }

        def fake_status(_host: str, remote_command: str, **_kwargs) -> str:
            vmid = remote_command.split()[2]
            return status_responses[vmid].pop(0)

        with mock.patch.object(haac, "find_duplicate_k3s_lxc_identities", return_value=duplicates):
            with mock.patch.object(haac, "run_proxmox_ssh") as run_proxmox_ssh:
                with mock.patch.object(haac, "run_proxmox_ssh_stdout", side_effect=fake_status):
                    with mock.patch("builtins.print") as fake_print:
                        quarantined = haac.quarantine_duplicate_k3s_lxc_identities("192.168.0.200", Path("tofu"))

        self.assertEqual(quarantined, duplicates)
        run_proxmox_ssh.assert_any_call("192.168.0.200", "pct set 104 -onboot 0")
        run_proxmox_ssh.assert_any_call("192.168.0.200", "pct shutdown 104 --timeout 60", check=False)
        run_proxmox_ssh.assert_any_call("192.168.0.200", "pct stop 104", check=False)
        run_proxmox_ssh.assert_any_call("192.168.0.200", "pct set 105 -onboot 0")
        fake_print.assert_any_call("[heal] Quarantined unmanaged duplicate LXC 104 (haacarr-worker2): hostname haacarr-worker2")
        fake_print.assert_any_call("[heal] Quarantined unmanaged duplicate LXC 105 (haacarr-worker1): IPv4 192.168.0.212")

    def test_cmd_run_ansible_repairs_node_identity_drift_before_refreshing_known_hosts(self) -> None:
        args = haac.argparse.Namespace(
            inventory="ansible/inventory.yml",
            playbook="ansible/playbook.yml",
            extra_args="",
        )
        events: list[str] = []

        def record(name: str):
            def inner(*_args, **_kwargs):
                events.append(name)
                return None

            return inner

        with mock.patch.object(haac, "merged_env", return_value={"HAAC_PROXMOX_ACCESS_HOST": "192.168.0.200"}):
            with mock.patch.object(haac, "ensure_repo_ssh_keypair", side_effect=record("repo-key")):
                with mock.patch.object(haac, "ensure_semaphore_ssh_keypair", side_effect=record("semaphore-key")):
                    with mock.patch.object(haac, "quarantine_duplicate_k3s_lxc_identities", side_effect=record("repair")):
                        with mock.patch.object(haac, "refresh_cluster_known_hosts", side_effect=record("known-hosts")):
                            with mock.patch.object(haac, "proxmox_access_host", return_value="192.168.0.200"):
                                with mock.patch.object(haac, "is_windows", return_value=True):
                                    with mock.patch.object(haac, "run_ansible_wsl", side_effect=record("ansible")):
                                        haac.cmd_run_ansible(args)

        self.assertEqual(events, ["repo-key", "semaphore-key", "repair", "known-hosts", "ansible"])


class TofuEnvMappingTests(unittest.TestCase):
    def test_tofu_tf_vars_includes_master_memory_input(self) -> None:
        env = {
            "LXC_PASSWORD": "demo-secret",
            "LXC_ROOTFS_DATASTORE": "local-zfs",
            "LXC_MASTER_HOSTNAME": "haacarr-master",
            "LXC_MASTER_MEMORY": "6144",
            "LXC_UNPRIVILEGED": "true",
            "LXC_NESTING": "true",
            "MASTER_TARGET_NODE": "pve",
            "K3S_MASTER_IP": "192.168.0.211/24",
            "WORKER_NODES_JSON": "{}",
            "HOST_NAS_PATH": "/mnt/pve/HaaC-Storage",
            "CLOUDFLARE_TUNNEL_TOKEN": "token",
            "DOMAIN_NAME": "example.com",
            "PROTONVPN_OPENVPN_USERNAME": "user",
            "PROTONVPN_OPENVPN_PASSWORD": "password",
            "SMB_USER": "smb-user",
            "SMB_PASSWORD": "smb-password",
            "NAS_ADDRESS": "192.168.0.50",
            "NAS_SHARE_NAME": "media",
            "STORAGE_UID": "1000",
            "STORAGE_GID": "1000",
            "PYTHON_CMD": "python",
        }

        with mock.patch.object(haac, "proxmox_access_host", return_value="192.168.0.200"):
            with mock.patch.object(haac, "resolve_default_gateway", return_value="192.168.0.1"):
                with mock.patch.object(haac, "maintenance_user", return_value="haac-maint"):
                    mapped = haac.tofu_tf_vars(env)

        self.assertEqual(mapped["TF_VAR_lxc_master_memory"], "6144")
        self.assertEqual(mapped["TF_VAR_proxmox_access_host"], "192.168.0.200")
        self.assertEqual(mapped["TF_VAR_lxc_gateway"], "192.168.0.1")


class GitopsStagePathTests(unittest.TestCase):
    def test_gitops_stage_paths_include_platform_generated_secrets(self) -> None:
        stage_paths = haac.gitops_stage_paths()

        self.assertIn(str(haac.SECRETS_DIR), stage_paths)
        self.assertIn(str(haac.ARGOCD_OIDC_SECRET_OUTPUT), stage_paths)
        self.assertIn(str(haac.LITMUS_ADMIN_SECRET_OUTPUT), stage_paths)
        self.assertIn(str(haac.LITMUS_MONGODB_SECRET_OUTPUT), stage_paths)
        self.assertIn(str(haac.MEDIA_AUTH_SECRET_OUTPUT), stage_paths)
        self.assertIn(str(haac.VALUES_OUTPUT), stage_paths)


class DownloadersRecoveryTests(unittest.TestCase):
    def test_recover_stalled_downloaders_rollout_returns_false_when_serviceaccount_is_missing(self) -> None:
        with mock.patch.object(
            haac,
            "run",
            return_value=mock.Mock(returncode=1, stdout="", stderr='Error from server (NotFound): serviceaccounts "downloaders-bootstrap" not found'),
        ) as run_mock:
            recovered = haac.recover_stalled_downloaders_rollout("kubectl", Path("demo-kubeconfig"))

        self.assertFalse(recovered)
        self.assertEqual(run_mock.call_count, 1)

    def test_recover_stalled_downloaders_rollout_returns_false_when_deployment_is_missing(self) -> None:
        responses = [
            mock.Mock(returncode=0, stdout="apiVersion: v1", stderr=""),
            mock.Mock(returncode=1, stdout="", stderr='Error from server (NotFound): deployments.apps "downloaders" not found'),
        ]
        with mock.patch.object(haac, "run", side_effect=responses) as run_mock:
            recovered = haac.recover_stalled_downloaders_rollout("kubectl", Path("demo-kubeconfig"))

        self.assertFalse(recovered)
        self.assertEqual(run_mock.call_count, 2)

    def test_argocd_hook_wait_resource_ref_supports_failed_phase(self) -> None:
        ref = haac.argocd_hook_wait_resource_ref(
            {
                "status": {
                    "operationState": {
                        "phase": "Failed",
                        "message": "waiting for completion of hook batch/Job/kube-prometheus-stack-admission-create",
                    }
                }
            }
        )

        self.assertEqual(
            ref,
            {
                "ref": "batch/Job/kube-prometheus-stack-admission-create",
                "group": "batch",
                "kind": "Job",
                "name": "kube-prometheus-stack-admission-create",
            },
        )


class SyncRepoTests(unittest.TestCase):
    def test_sync_repo_fast_forwards_before_checkpoint_when_remote_is_ahead(self) -> None:
        fetch_result = mock.Mock(returncode=0, stdout="", stderr="")
        merge_result = mock.Mock(returncode=0, stdout="", stderr="")
        run_calls: list[list[str]] = []

        def fake_run(command, **kwargs):
            run_calls.append(command)
            if command[:3] == ["git", "fetch", "origin"]:
                return fetch_result
            if command[:3] == ["git", "merge", "--ff-only"]:
                return merge_result
            self.fail(f"unexpected run call: {command}")

        with mock.patch.object(haac, "merged_env", return_value={"GITOPS_REPO_URL": "https://github.com/daubog44/arr_setup.git", "GITOPS_REPO_REVISION": "main"}):
            with mock.patch.object(haac, "require_git_bootstrap_repo"):
                with mock.patch.object(haac, "run", side_effect=fake_run):
                    with mock.patch.object(haac.gitstatelib, "git_ref_state", return_value="behind"):
                        with mock.patch.object(haac.gitstatelib, "git_tracked_dirty_paths", return_value=["k8s/demo.yaml"]):
                            with mock.patch.object(haac, "stash_tracked_git_changes", return_value="stash@{0}") as stash:
                                with mock.patch.object(haac, "restore_tracked_git_changes") as restore:
                                    with mock.patch.object(haac, "checkpoint_git_changes") as checkpoint:
                                        haac.sync_repo()

        self.assertEqual(run_calls[0][:3], ["git", "fetch", "origin"])
        self.assertEqual(run_calls[1][:3], ["git", "merge", "--ff-only"])
        stash.assert_called_once_with(["k8s/demo.yaml"], message="haac-sync-preserve-tracked")
        restore.assert_called_once_with("stash@{0}")
        checkpoint.assert_called_once_with(
            "Auto-save before sync [skip ci]",
            empty_message="[ok] GitOps repo already checkpointed before sync.",
            paths=["k8s/demo.yaml"],
        )

    def test_sync_repo_checkpoint_only_stages_tracked_paths_when_equal(self) -> None:
        fetch_result = mock.Mock(returncode=0, stdout="", stderr="")

        with mock.patch.object(haac, "merged_env", return_value={"GITOPS_REPO_URL": "https://github.com/daubog44/arr_setup.git", "GITOPS_REPO_REVISION": "main"}):
            with mock.patch.object(haac, "require_git_bootstrap_repo"):
                with mock.patch.object(haac, "run", return_value=fetch_result):
                    with mock.patch.object(haac.gitstatelib, "git_ref_state", return_value="equal"):
                        with mock.patch.object(haac.gitstatelib, "git_tracked_dirty_paths", return_value=["k8s/demo.yaml"]):
                            with mock.patch.object(haac, "checkpoint_git_changes") as checkpoint:
                                haac.sync_repo()

        checkpoint.assert_called_once_with(
            "Auto-save before sync [skip ci]",
            empty_message="[ok] GitOps repo already checkpointed before sync.",
            paths=["k8s/demo.yaml"],
        )

    def test_sync_repo_equal_with_only_untracked_paths_skips_checkpoint(self) -> None:
        fetch_result = mock.Mock(returncode=0, stdout="", stderr="")

        with mock.patch.object(haac, "merged_env", return_value={"GITOPS_REPO_URL": "https://github.com/daubog44/arr_setup.git", "GITOPS_REPO_REVISION": "main"}):
            with mock.patch.object(haac, "require_git_bootstrap_repo"):
                with mock.patch.object(haac, "run", return_value=fetch_result):
                    with mock.patch.object(haac.gitstatelib, "git_ref_state", return_value="equal"):
                        with mock.patch.object(haac.gitstatelib, "git_tracked_dirty_paths", return_value=[]):
                            with mock.patch.object(haac, "checkpoint_git_changes") as checkpoint:
                                haac.sync_repo()

        checkpoint.assert_not_called()

    def test_sync_repo_restore_conflict_keeps_stash_and_raises(self) -> None:
        fetch_result = mock.Mock(returncode=0, stdout="", stderr="")
        merge_result = mock.Mock(returncode=0, stdout="", stderr="")
        run_calls: list[list[str]] = []

        def fake_run(command, **kwargs):
            run_calls.append(command)
            if command[:3] == ["git", "fetch", "origin"]:
                return fetch_result
            if command[:3] == ["git", "merge", "--ff-only"]:
                return merge_result
            self.fail(f"unexpected run call: {command}")

        with mock.patch.object(haac, "merged_env", return_value={"GITOPS_REPO_URL": "https://github.com/daubog44/arr_setup.git", "GITOPS_REPO_REVISION": "main"}):
            with mock.patch.object(haac, "require_git_bootstrap_repo"):
                with mock.patch.object(haac, "run", side_effect=fake_run):
                    with mock.patch.object(haac.gitstatelib, "git_ref_state", return_value="behind"):
                        with mock.patch.object(haac.gitstatelib, "git_tracked_dirty_paths", return_value=["k8s/demo.yaml"]):
                            with mock.patch.object(haac, "stash_tracked_git_changes", return_value="stash@{0}") as stash:
                                with mock.patch.object(haac, "restore_tracked_git_changes", side_effect=haac.HaaCError("restore-conflict")) as restore:
                                    with mock.patch.object(haac, "checkpoint_git_changes") as checkpoint:
                                        with self.assertRaisesRegex(haac.HaaCError, "restore-conflict"):
                                            haac.sync_repo()

        self.assertEqual(run_calls[0][:3], ["git", "fetch", "origin"])
        self.assertEqual(run_calls[1][:3], ["git", "merge", "--ff-only"])
        stash.assert_called_once_with(["k8s/demo.yaml"], message="haac-sync-preserve-tracked")
        restore.assert_called_once_with("stash@{0}")
        checkpoint.assert_not_called()

    def test_sync_repo_stops_on_untracked_collision_with_remote(self) -> None:
        fetch_result = mock.Mock(returncode=0, stdout="", stderr="")

        with mock.patch.object(haac, "merged_env", return_value={"GITOPS_REPO_URL": "https://github.com/daubog44/arr_setup.git", "GITOPS_REPO_REVISION": "main"}):
            with mock.patch.object(haac, "require_git_bootstrap_repo"):
                with mock.patch.object(haac, "run", return_value=fetch_result):
                    with mock.patch.object(haac.gitstatelib, "git_ref_state", return_value="behind"):
                        with mock.patch.object(haac.gitstatelib, "git_tracked_dirty_paths", return_value=[]):
                            with mock.patch.object(haac.gitstatelib, "git_paths_at_ref", return_value={"incoming.yaml"}):
                                with mock.patch.object(haac.gitstatelib, "git_untracked_paths", return_value=["incoming.yaml", "scratch.txt"]):
                                    with self.assertRaisesRegex(haac.HaaCError, "incoming.yaml"):
                                        haac.sync_repo()


class GitStateHelperTests(unittest.TestCase):
    def test_git_status_helpers_split_tracked_and_untracked_paths(self) -> None:
        completed = mock.Mock(
            returncode=0,
            stdout=" M tracked.yaml\nR  old.yaml -> renamed.yaml\n?? scratch.txt\n",
            stderr="",
        )

        with mock.patch.object(haac.gitstatelib.subprocess, "run", return_value=completed):
            entries = haac.gitstatelib.git_status_entries(ROOT)
            tracked = haac.gitstatelib.git_tracked_dirty_paths(ROOT)
            untracked = haac.gitstatelib.git_untracked_paths(ROOT)

        self.assertEqual(entries, [(" M", "tracked.yaml"), ("R ", "renamed.yaml"), ("??", "scratch.txt")])
        self.assertEqual(tracked, ["tracked.yaml", "renamed.yaml"])
        self.assertEqual(untracked, ["scratch.txt"])

    def test_git_paths_at_ref_returns_tracked_paths(self) -> None:
        completed = mock.Mock(returncode=0, stdout="k8s/demo.yaml\nREADME.md\n", stderr="")

        with mock.patch.object(haac.gitstatelib.subprocess, "run", return_value=completed):
            paths = haac.gitstatelib.git_paths_at_ref(ROOT, "origin/main")

        self.assertEqual(paths, {"k8s/demo.yaml", "README.md"})

    def test_git_tracked_paths_under_returns_matching_entries(self) -> None:
        completed = mock.Mock(returncode=0, stdout=".playwright-cli/page.yml\n.playwright-cli/state.json\n", stderr="")

        with mock.patch.object(haac.gitstatelib.subprocess, "run", return_value=completed):
            paths = haac.gitstatelib.git_tracked_paths_under(ROOT, ".playwright-cli")

        self.assertEqual(paths, {".playwright-cli/page.yml", ".playwright-cli/state.json"})


class PushChangesTests(unittest.TestCase):
    def test_push_changes_unwinds_generated_commit_when_remote_moves_during_push(self) -> None:
        ok = mock.Mock(returncode=0, stdout="", stderr="")
        push_fail = mock.Mock(returncode=1, stdout="", stderr="! [rejected] main -> main (fetch first)")
        run_calls: list[list[str]] = []

        def fake_run(command, **kwargs):
            run_calls.append(command)
            if command[:3] == ["git", "fetch", "origin"]:
                return ok
            if command[:3] == ["git", "commit", "-m"]:
                return ok
            if command[:3] == ["git", "push", "origin"]:
                return push_fail
            if command[:3] == ["git", "reset", "--mixed"]:
                return ok
            self.fail(f"unexpected run call: {command}")

        with mock.patch.object(
            haac,
            "merged_env",
            return_value={"GITOPS_REPO_URL": "https://github.com/daubog44/arr_setup.git", "GITOPS_REPO_REVISION": "main"},
        ):
            with mock.patch.object(haac, "require_git_bootstrap_repo"):
                with mock.patch.object(haac, "run", side_effect=fake_run):
                    with mock.patch.object(haac.gitstatelib, "git_ref_state", side_effect=["equal", "equal", "diverged"]):
                        with mock.patch.object(haac, "generate_secrets_core"):
                            with mock.patch.object(haac, "stage_git_paths"):
                                with mock.patch.object(haac, "git_has_staged_changes", return_value=True):
                                    with mock.patch.object(haac, "run_stdout", return_value="deadbeef"):
                                        with self.assertRaisesRegex(haac.HaaCError, "remote branch moved during the final push"):
                                            haac.push_changes(False, "kubectl", Path("demo-kubeconfig"))

        self.assertIn(["git", "reset", "--mixed", "HEAD~1"], run_calls)


class LitmusChaosCatalogTests(unittest.TestCase):
    def test_load_litmus_chaos_catalog_reads_manifests_and_supporting_yaml(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            catalog_dir = Path(temp_dir)
            (catalog_dir / "workflow.json").write_text('{"apiVersion":"litmuschaos.io/v1alpha1","kind":"ChaosEngine"}', encoding="utf-8")
            (catalog_dir / "workflow.yaml").write_text("apiVersion: litmuschaos.io/v1alpha1\nkind: ChaosEngine\n", encoding="utf-8")
            (catalog_dir / "pod-delete-chaosexperiment.yaml").write_text(
                "apiVersion: litmuschaos.io/v1alpha1\nkind: ChaosExperiment\n",
                encoding="utf-8",
            )
            (catalog_dir / "catalog.json").write_text(
                json.dumps(
                    {
                        "experiments": [
                            {
                                "name": "demo-chaos",
                                "description": "Demo workflow",
                                "manifest": "workflow.json",
                                "sourceManifest": "workflow.yaml",
                                "supportingManifests": ["pod-delete-chaosexperiment.yaml"],
                                "tags": ["haac", "demo"],
                            }
                        ]
                    }
                ),
                encoding="utf-8",
            )

            catalog = haac.load_litmus_chaos_catalog(catalog_dir / "catalog.json")

        self.assertEqual(len(catalog), 1)
        self.assertEqual(catalog[0]["name"], "demo-chaos")
        self.assertEqual(catalog[0]["description"], "Demo workflow")
        self.assertIn('"kind":"ChaosEngine"', catalog[0]["manifest"])
        self.assertIn("kind: ChaosEngine", catalog[0]["source_manifest"])
        self.assertTrue(catalog[0]["manifest_path"].endswith("workflow.json"))
        self.assertTrue(catalog[0]["source_manifest_path"].endswith("workflow.yaml"))
        self.assertEqual(
            catalog[0]["supporting_manifest_paths"],
            [str(catalog_dir / "pod-delete-chaosexperiment.yaml")],
        )
        self.assertEqual(catalog[0]["tags"], ["demo", "haac"])

    def test_load_litmus_chaos_catalog_rejects_supporting_manifest_path_escape(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            catalog_dir = Path(temp_dir)
            escaped_manifest = catalog_dir.parent / "escape.yaml"
            escaped_manifest.write_text("apiVersion: litmuschaos.io/v1alpha1\nkind: ChaosExperiment\nmetadata:\n  namespace: litmus\n", encoding="utf-8")
            (catalog_dir / "workflow.json").write_text('{"apiVersion":"litmuschaos.io/v1alpha1","kind":"ChaosEngine"}', encoding="utf-8")
            (catalog_dir / "catalog.json").write_text(
                json.dumps(
                    {
                        "experiments": [
                            {
                                "name": "demo-chaos",
                                "description": "Demo workflow",
                                "manifest": "workflow.json",
                                "supportingManifests": ["..\\escape.yaml"],
                            }
                        ]
                    }
                ),
                encoding="utf-8",
            )

            with self.assertRaisesRegex(haac.HaaCError, "escapes the Litmus chaos catalog root"):
                haac.load_litmus_chaos_catalog(catalog_dir / "catalog.json")

    def test_ensure_litmus_supporting_manifests_dedupes_and_validates(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            catalog_dir = Path(temp_dir)
            support = catalog_dir / "pod-delete-chaosexperiment.yaml"
            support.write_text(
                "apiVersion: litmuschaos.io/v1alpha1\nkind: ChaosExperiment\nmetadata:\n  name: pod-delete\n  namespace: litmus\n",
                encoding="utf-8",
            )
            catalog = [
                {"supporting_manifest_paths": [str(support)]},
                {"supporting_manifest_paths": [str(support)]},
            ]

            with mock.patch.object(haac, "run") as run_mock:
                haac.ensure_litmus_supporting_manifests("kubectl", Path("demo-kubeconfig"), catalog)

        run_mock.assert_called_once_with(
            ["kubectl", "--kubeconfig", "demo-kubeconfig", "apply", "-f", "-"],
            input_text="apiVersion: litmuschaos.io/v1alpha1\nkind: ChaosExperiment\nmetadata:\n  name: pod-delete\n  namespace: litmus",
        )

    def test_ensure_litmus_supporting_manifests_rejects_non_chaosexperiment(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            support = Path(temp_dir) / "bad.yaml"
            support.write_text(
                "apiVersion: v1\nkind: ConfigMap\nmetadata:\n  name: bad\n  namespace: litmus\n",
                encoding="utf-8",
            )
            catalog = [{"supporting_manifest_paths": [str(support)]}]

            with self.assertRaisesRegex(haac.HaaCError, "must define kind ChaosExperiment"):
                haac.ensure_litmus_supporting_manifests("kubectl", Path("demo-kubeconfig"), catalog)

    def test_ensure_litmus_chaos_catalog_seeds_missing_experiments(self) -> None:
        catalog = [
            {
                "name": "demo-chaos",
                "description": "Demo workflow",
                "manifest": '{"apiVersion":"litmuschaos.io/v1alpha1","kind":"ChaosEngine","metadata":{"name":"demo-chaos"}}',
                "supporting_manifest_paths": [],
                "tags": ["demo", "haac"],
            }
        ]

        with mock.patch.object(haac, "load_litmus_chaos_catalog", return_value=catalog):
            with mock.patch.object(haac, "ensure_litmus_supporting_manifests") as ensure_support:
                with mock.patch.object(haac, "litmus_list_experiments", return_value=[]):
                    with mock.patch.object(haac, "litmus_save_experiment", return_value="saved") as save_experiment:
                        with mock.patch("builtins.print") as fake_print:
                            haac.ensure_litmus_chaos_catalog(
                                9002,
                                "token",
                                "project",
                                infra_id="infra-1",
                                kubectl="kubectl",
                                kubeconfig=Path("demo-kubeconfig"),
                            )

        ensure_support.assert_called_once_with("kubectl", Path("demo-kubeconfig"), catalog)
        save_experiment.assert_called_once_with(
            9002,
            "token",
            project_id="project",
            experiment_id=haac.litmus_catalog_entry_id("demo-chaos"),
            infra_id="infra-1",
            name="demo-chaos",
            description="Demo workflow",
            manifest='{"apiVersion":"litmuschaos.io/v1alpha1","kind":"ChaosEngine","metadata":{"name":"demo-chaos"}}',
            tags=["demo", "haac"],
        )
        fake_print.assert_any_call("[ok] Litmus chaos experiment seeded: demo-chaos")

    def test_ensure_litmus_chaos_catalog_keeps_matching_experiments_without_update(self) -> None:
        catalog = [
            {
                "name": "demo-chaos",
                "description": "Demo workflow",
                "manifest": '{"apiVersion":"litmuschaos.io/v1alpha1","kind":"ChaosEngine","metadata":{"name":"demo-chaos","labels":{"workflow_id":"dynamic","revision_id":"dynamic","infra_id":"infra-1"}}}',
                "supporting_manifest_paths": [],
                "tags": ["demo", "haac"],
            },
        ]
        existing = [
            {
                "experimentID": "exp-1",
                "name": "demo-chaos",
                "description": "Demo workflow",
                "tags": ["haac", "demo"],
                "experimentManifest": '{"apiVersion":"litmuschaos.io/v1alpha1","kind":"ChaosEngine","metadata":{"name":"demo-chaos","labels":{"workflow_id":"server","revision_id":"server","infra_id":"infra-1"}}}',
                "infra": {"infraID": "infra-1"},
            },
        ]

        with mock.patch.object(haac, "load_litmus_chaos_catalog", return_value=catalog):
            with mock.patch.object(haac, "ensure_litmus_supporting_manifests"):
                with mock.patch.object(haac, "litmus_list_experiments", return_value=existing):
                    with mock.patch.object(haac, "litmus_save_experiment") as save_experiment:
                        with mock.patch("builtins.print") as fake_print:
                            haac.ensure_litmus_chaos_catalog(
                                9002,
                                "token",
                                "project",
                                infra_id="infra-1",
                                kubectl="kubectl",
                                kubeconfig=Path("demo-kubeconfig"),
                            )

        save_experiment.assert_not_called()
        fake_print.assert_any_call("[ok] Litmus chaos experiment already seeded: demo-chaos")

    def test_ensure_litmus_chaos_catalog_updates_drifted_experiments(self) -> None:
        catalog = [
            {
                "name": "demo-chaos",
                "description": "Expected description",
                "manifest": '{"apiVersion":"litmuschaos.io/v1alpha1","kind":"ChaosEngine","metadata":{"name":"demo-chaos"}}',
                "supporting_manifest_paths": [],
                "tags": ["demo", "haac"],
            }
        ]
        existing = [
            {
                "experimentID": "exp-1",
                "name": "demo-chaos",
                "description": "Portal description",
                "tags": ["haac"],
                "experimentManifest": '{"apiVersion":"litmuschaos.io/v1alpha1","kind":"ChaosEngine","metadata":{"name":"demo-chaos"}}',
                "infra": {"infraID": "infra-old"},
            }
        ]

        with mock.patch.object(haac, "load_litmus_chaos_catalog", return_value=catalog):
            with mock.patch.object(haac, "ensure_litmus_supporting_manifests"):
                with mock.patch.object(haac, "litmus_list_experiments", return_value=existing):
                    with mock.patch.object(haac, "litmus_save_experiment", return_value="updated") as save_experiment:
                        with mock.patch("builtins.print") as fake_print:
                            haac.ensure_litmus_chaos_catalog(
                                9002,
                                "token",
                                "project",
                                infra_id="infra-1",
                                kubectl="kubectl",
                                kubeconfig=Path("demo-kubeconfig"),
                            )

        save_experiment.assert_called_once_with(
            9002,
            "token",
            project_id="project",
            experiment_id="exp-1",
            infra_id="infra-1",
            name="demo-chaos",
            description="Expected description",
            manifest='{"apiVersion":"litmuschaos.io/v1alpha1","kind":"ChaosEngine","metadata":{"name":"demo-chaos"}}',
            tags=["demo", "haac"],
        )
        fake_print.assert_any_call("[ok] Litmus chaos experiment updated: demo-chaos")


class LitmusBootstrapRecoveryTests(unittest.TestCase):
    def test_retry_litmus_transient_retries_remote_disconnect_then_succeeds(self) -> None:
        attempts: list[str] = []

        def flaky_action() -> str:
            attempts.append("x")
            if len(attempts) == 1:
                raise haac.HaaCError("Remote end closed connection without response")
            return "ok"

        with mock.patch.object(haac.time, "sleep") as sleep_mock:
            result = haac.retry_litmus_transient(flaky_action, context="Litmus demo action", attempts=3, sleep_seconds=2)

        self.assertEqual(result, "ok")
        self.assertEqual(len(attempts), 2)
        sleep_mock.assert_called_once_with(2)

    def test_wait_for_litmus_core_rollout_checks_auth_and_server(self) -> None:
        with mock.patch.object(haac, "run") as run_mock:
            haac.wait_for_litmus_core_rollout("kubectl", Path("demo-kubeconfig"))

        run_mock.assert_has_calls(
            [
                mock.call(
                    [
                        "kubectl",
                        "--kubeconfig",
                        "demo-kubeconfig",
                        "rollout",
                        "status",
                        "deployment/litmus-auth-server",
                        "-n",
                        "chaos",
                        "--timeout=240s",
                    ]
                ),
                mock.call(
                    [
                        "kubectl",
                        "--kubeconfig",
                        "demo-kubeconfig",
                        "rollout",
                        "status",
                        "deployment/litmus-server",
                        "-n",
                        "chaos",
                        "--timeout=240s",
                    ]
                ),
            ]
        )

    def test_reconcile_litmus_chaos_repairs_admin_before_login(self) -> None:
        call_order: list[str] = []

        @contextlib.contextmanager
        def fake_cluster_session(*args: object, **kwargs: object):
            yield Path("session-kubeconfig")

        @contextlib.contextmanager
        def fake_port_forward(*args: object, **kwargs: object):
            yield 9001

        def fake_run(args: list[str], check: bool = True, **kwargs: object) -> subprocess.CompletedProcess[str]:
            return subprocess.CompletedProcess(args, 0, "", "")

        def fake_kubectl_json(*args: object, **kwargs: object) -> dict[str, object]:
            command = list(args[2])
            if command[:3] == ["get", "svc", "litmus-auth-server-service"]:
                return {"spec": {"ports": [{"name": "auth-server", "port": 9003}]}}
            if command[:3] == ["get", "svc", "litmus-server-service"]:
                return {"spec": {"ports": [{"port": 9002}]}}
            if command[:3] == ["get", "secret", haac.LITMUS_MONGODB_SECRET_NAME]:
                return {"data": {}}
            raise AssertionError(command)

        def fake_wait_for_core(*args: object, **kwargs: object) -> None:
            call_order.append("wait_for_core")

        def fake_reconcile_admin(*args: object, **kwargs: object) -> None:
            call_order.append("repair_admin")

        def fake_auth_login(*args: object, **kwargs: object) -> dict[str, object]:
            call_order.append("auth_login")
            return {"projectID": "project-1", "accessToken": "token-1"}

        with mock.patch.object(haac, "cluster_session", fake_cluster_session):
            with mock.patch.object(haac, "run", side_effect=fake_run):
                with mock.patch.object(haac, "wait_for_litmus_core_rollout", side_effect=fake_wait_for_core):
                    with mock.patch.object(haac, "reconcile_litmus_admin_session", side_effect=fake_reconcile_admin):
                        with mock.patch.object(haac, "kubectl_json", side_effect=fake_kubectl_json):
                            with mock.patch.object(haac, "decode_secret_data", return_value={"mongodb-root-password": "secret"}):
                                with mock.patch.object(haac, "kubectl_port_forward", fake_port_forward):
                                    with mock.patch.object(haac, "litmus_auth_login", side_effect=fake_auth_login):
                                        with mock.patch.object(haac, "litmus_list_environments", return_value=[]):
                                            with mock.patch.object(
                                                haac,
                                                "select_litmus_reconcile_targets",
                                                return_value=[("haac-default", "haac-default", True)],
                                            ):
                                                with mock.patch.object(
                                                    haac,
                                                    "reconcile_litmus_environment_target",
                                                    return_value={"infraID": "infra-1", "name": "haac-default"},
                                                ):
                                                    with mock.patch.object(haac, "litmus_hide_legacy_environment", return_value=False):
                                                        with mock.patch.object(haac, "ensure_litmus_chaos_catalog"):
                                                            haac.reconcile_litmus_chaos(
                                                                "192.168.0.211",
                                                                "192.168.0.200",
                                                                Path("demo-kubeconfig"),
                                                                "kubectl",
                                                            )

        self.assertEqual(call_order[:3], ["wait_for_core", "repair_admin", "auth_login"])


class SecuritySignalResidueCleanupTests(unittest.TestCase):
    def test_cleanup_security_signal_residue_in_session_deletes_reports_for_zero_replica_replicasets(self) -> None:
        def fake_kubectl_json(
            kubectl: str,
            kubeconfig: Path,
            command: list[str],
            *,
            context: str,
        ) -> dict[str, object]:
            resource = command[1]
            namespace = command[3]
            if resource == "replicaset" and namespace == "argocd":
                return {
                    "items": [
                        {"metadata": {"name": "argocd-server-old"}, "spec": {"replicas": 0}, "status": {}},
                        {
                            "metadata": {"name": "argocd-server-live"},
                            "spec": {"replicas": 1},
                            "status": {"readyReplicas": 1, "availableReplicas": 1},
                        },
                    ]
                }
            if resource == "replicaset" and namespace == "security":
                return {
                    "items": [
                        {"metadata": {"name": "trivy-operator-old"}, "spec": {"replicas": 0}, "status": {}},
                    ]
                }
            if resource == "policyreport" and namespace == "argocd":
                return {
                    "items": [
                        {
                            "metadata": {"namespace": "argocd", "name": "policy-old"},
                            "scope": {"kind": "ReplicaSet", "name": "argocd-server-old"},
                        },
                        {
                            "metadata": {"namespace": "argocd", "name": "policy-live"},
                            "scope": {"kind": "ReplicaSet", "name": "argocd-server-live"},
                        },
                    ]
                }
            if resource == "policyreport" and namespace == "security":
                return {
                    "items": [
                        {
                            "metadata": {"namespace": "security", "name": "policy-sec"},
                            "scope": {"kind": "ReplicaSet", "name": "trivy-operator-old"},
                        }
                    ]
                }
            if resource == "configauditreports.aquasecurity.github.io" and namespace == "security":
                return {
                    "items": [
                        {
                            "metadata": {
                                "namespace": "security",
                                "name": "config-sec",
                                "ownerReferences": [{"kind": "ReplicaSet", "name": "trivy-operator-old"}],
                            }
                        }
                    ]
                }
            if resource == "vulnerabilityreports.aquasecurity.github.io" and namespace == "argocd":
                return {
                    "items": [
                        {
                            "metadata": {
                                "namespace": "argocd",
                                "name": "vuln-old",
                                "ownerReferences": [{"kind": "ReplicaSet", "name": "argocd-server-old"}],
                            }
                        }
                    ]
                }
            return {"items": []}

        def fake_run(command: list[str], **kwargs: object) -> mock.Mock:
            return mock.Mock(args=command, returncode=0, stdout="", stderr="")

        with mock.patch.object(haac, "kubectl_json", side_effect=fake_kubectl_json):
            with mock.patch.object(haac, "run", side_effect=fake_run) as run_mock:
                counts = haac.cleanup_security_signal_residue_in_session(
                    "kubectl",
                    Path("demo-kubeconfig"),
                    targets={
                        "argocd": ("argocd-server-",),
                        "security": ("trivy-operator-",),
                    },
                )

        self.assertEqual(
            counts,
            {"policy_reports": 2, "trivy_reports": 2, "replicasets": 2},
        )
        deleted_commands = [call.args[0] for call in run_mock.call_args_list]
        self.assertIn(
            ["kubectl", "--kubeconfig", "demo-kubeconfig", "delete", "policyreport", "policy-old", "-n", "argocd", "--ignore-not-found=true"],
            deleted_commands,
        )
        self.assertIn(
            ["kubectl", "--kubeconfig", "demo-kubeconfig", "delete", "policyreport", "policy-sec", "-n", "security", "--ignore-not-found=true"],
            deleted_commands,
        )
        self.assertIn(
            [
                "kubectl",
                "--kubeconfig",
                "demo-kubeconfig",
                "delete",
                "configauditreports.aquasecurity.github.io",
                "config-sec",
                "-n",
                "security",
                "--ignore-not-found=true",
            ],
            deleted_commands,
        )
        self.assertIn(
            [
                "kubectl",
                "--kubeconfig",
                "demo-kubeconfig",
                "delete",
                "vulnerabilityreports.aquasecurity.github.io",
                "vuln-old",
                "-n",
                "argocd",
                "--ignore-not-found=true",
            ],
            deleted_commands,
        )
        self.assertIn(
            ["kubectl", "--kubeconfig", "demo-kubeconfig", "delete", "replicaset", "argocd-server-old", "-n", "argocd", "--ignore-not-found=true"],
            deleted_commands,
        )
        self.assertIn(
            ["kubectl", "--kubeconfig", "demo-kubeconfig", "delete", "replicaset", "trivy-operator-old", "-n", "security", "--ignore-not-found=true"],
            deleted_commands,
        )

    def test_cleanup_preserves_zero_replica_replicaset_without_matching_reports(self) -> None:
        def fake_kubectl_json(
            kubectl: str,
            kubeconfig: Path,
            command: list[str],
            *,
            context: str,
        ) -> dict[str, object]:
            resource = command[1]
            namespace = command[3]
            if resource == "replicaset" and namespace == "argocd":
                return {
                    "items": [
                        {"metadata": {"name": "argocd-server-old"}, "spec": {"replicas": 0}, "status": {}},
                    ]
                }
            return {"items": []}

        delete_calls: list[list[str]] = []

        def fake_run(command: list[str], **kwargs: object) -> mock.Mock:
            delete_calls.append(command)
            return mock.Mock(returncode=0, stdout="", stderr="")

        with mock.patch.object(haac, "kubectl_json", side_effect=fake_kubectl_json):
            with mock.patch.object(haac, "run", side_effect=fake_run):
                counts = haac.cleanup_security_signal_residue_in_session(
                    "kubectl",
                    Path("demo-kubeconfig"),
                    targets={"argocd": ("argocd-server-",)},
                )

        self.assertEqual(
            counts,
            {"policy_reports": 0, "trivy_reports": 0, "replicasets": 0},
        )
        self.assertEqual(delete_calls, [])


class CleanLocalArtifactsTests(unittest.TestCase):
    def test_clean_local_artifacts_removes_disposable_roots_and_prunes_empty_tmp_dirs(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            playwright_cli = root / ".playwright-cli"
            playwright_cli.mkdir()
            (playwright_cli / "page.yml").write_text("snapshot", encoding="utf-8")
            tmp_root = root / ".tmp"
            empty_scratch = tmp_root / "kube-sessions" / "old"
            empty_scratch.mkdir(parents=True)
            populated_scratch = tmp_root / "secrets-runtime" / "keep"
            populated_scratch.mkdir(parents=True)
            (populated_scratch / "secret.txt").write_text("keep", encoding="utf-8")
            tracked_file = root / "keep.txt"
            tracked_file.write_text("keep", encoding="utf-8")

            with mock.patch.object(haac, "ROOT", root):
                with mock.patch.object(haac, "LEGACY_ARTIFACT_DIRS", (playwright_cli,)):
                    with mock.patch.object(haac, "SANCTIONED_SCRATCH_ROOTS", (tmp_root,)):
                        with mock.patch.object(haac, "LEGACY_ARTIFACT_PATTERNS", ()):
                            haac.clean_local_artifacts()

            self.assertFalse(playwright_cli.exists())
            self.assertTrue(tmp_root.exists())
            self.assertFalse(empty_scratch.exists())
            self.assertTrue(populated_scratch.exists())
            self.assertEqual(tracked_file.read_text(encoding="utf-8"), "keep")

    def test_clean_local_artifacts_does_not_remove_regular_repo_paths(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            microsoft_root = root / "Microsoft"
            (microsoft_root / "docs").mkdir(parents=True)
            kept_file = microsoft_root / "docs" / "keep.txt"
            kept_file.write_text("keep", encoding="utf-8")

            with mock.patch.object(haac, "ROOT", root):
                with mock.patch.object(haac, "LEGACY_ARTIFACT_DIRS", ()):
                    with mock.patch.object(haac, "SANCTIONED_SCRATCH_ROOTS", (root / ".tmp",)):
                        with mock.patch.object(haac, "LEGACY_ARTIFACT_PATTERNS", ()):
                            haac.clean_local_artifacts()

            self.assertTrue(microsoft_root.exists())
            self.assertEqual(kept_file.read_text(encoding="utf-8"), "keep")

    def test_clean_local_artifacts_skips_listed_roots_if_git_still_tracks_them(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            tracked_root = root / ".playwright-cli"
            tracked_root.mkdir()
            tracked_file = tracked_root / "page.yml"
            tracked_file.write_text("tracked", encoding="utf-8")

            with mock.patch.object(haac, "ROOT", root):
                with mock.patch.object(haac, "LEGACY_ARTIFACT_DIRS", (tracked_root,)):
                    with mock.patch.object(haac, "SANCTIONED_SCRATCH_ROOTS", (root / ".tmp",)):
                        with mock.patch.object(haac, "LEGACY_ARTIFACT_PATTERNS", ()):
                            with mock.patch.object(haac.gitstatelib, "git_tracked_paths_under", return_value={".playwright-cli/page.yml"}):
                                haac.clean_local_artifacts()

            self.assertTrue(tracked_root.exists())
            self.assertEqual(tracked_file.read_text(encoding="utf-8"), "tracked")


class DownloadersTemplateContractTests(unittest.TestCase):
    def test_qbittorrent_exporter_uses_secret_backed_username(self) -> None:
        template = (
            haac.K8S_DIR / "charts" / "haac-stack" / "charts" / "downloaders" / "templates" / "downloaders.yaml"
        ).read_text(encoding="utf-8")

        self.assertIn(
            '            - name: QBITTORRENT_USERNAME\n              valueFrom:\n                secretKeyRef:\n                  name: downloaders-auth\n                  key: QBITTORRENT_USERNAME',
            template,
        )

    def test_downloaders_template_reconciles_supported_shared_paths(self) -> None:
        template = (
            haac.K8S_DIR / "charts" / "haac-stack" / "charts" / "downloaders" / "templates" / "downloaders.yaml"
        ).read_text(encoding="utf-8")

        self.assertIn('checksum/protonvpn-secret: {{ .Values.global.auth.protonvpnSecretChecksum | quote }}', template)
        self.assertIn("value: /data/torrents", template)
        self.assertIn("value: /data/torrents/incomplete", template)
        self.assertIn("parser = configparser.RawConfigParser(interpolation=None)", template)
        self.assertIn('parser["BitTorrent"]["Session\\\\DefaultSavePath"] = os.environ["QBITTORRENT_SAVE_PATH"]', template)
        self.assertIn('parser["Preferences"]["Downloads\\\\TempPathEnabled"] = "true"', template)
        self.assertIn('"queueing_enabled":true', template)
        self.assertIn('"max_active_downloads":8', template)
        self.assertIn('"dont_count_slow_torrents":true', template)
        self.assertIn('qBittorrent did not persist the supported shared download paths.', template)
        self.assertIn("/api/v2/torrents/createCategory", template)
        self.assertIn("/api/v2/torrents/editCategory", template)
        self.assertIn('qbit_upsert_category "lidarr" "/data/torrents/lidarr"', template)
        self.assertIn('qbit_upsert_category "whisparr" "/data/torrents/whisparr"', template)
        self.assertIn('qbit_upsert_category "lidarr-imported" "/data/torrents/lidarr-imported"', template)
        self.assertIn('qbit_upsert_category "whisparr-imported" "/data/torrents/whisparr-imported"', template)
        self.assertIn('case "$create_code" in', template)
        self.assertIn('200|409', template)
        self.assertIn('case "$edit_code" in', template)
        self.assertIn("qBittorrent category routing reconciled.", template)

    def test_downloaders_readiness_probe_accepts_qui_ready_and_qbit_403(self) -> None:
        script = haac.downloaders_readiness_probe_script()

        self.assertIn("http://127.0.0.1:7476/api/auth/me", script)
        self.assertIn("http://127.0.0.1:8080/api/v2/app/version", script)
        self.assertIn("'200 403'", script)

    def test_qbittorrent_shared_paths_supported_requires_repo_managed_paths(self) -> None:
        supported = "\n".join(
            (
                "[BitTorrent]",
                "Session\\DefaultSavePath=/data/torrents/",
                "Session\\TempPath=/data/torrents/incomplete/",
                "[Preferences]",
                "Downloads\\SavePath=/data/torrents/",
                "Downloads\\TempPath=/data/torrents/incomplete/",
            )
        )
        unsupported = supported.replace("/data/torrents/", "/downloads/")

        self.assertTrue(haac.qbittorrent_shared_paths_supported(supported))
        self.assertFalse(haac.qbittorrent_shared_paths_supported(unsupported))

    def test_qbittorrent_managed_category_paths_cover_arr_clients_and_imported_buckets(self) -> None:
        self.assertEqual(
            haac.ARR_QBITTORRENT_CATEGORY_SAVE_PATHS,
            {
                "radarr": "/data/torrents/radarr",
                "tv-sonarr": "/data/torrents/tv-sonarr",
                "lidarr": "/data/torrents/lidarr",
                "whisparr": "/data/torrents/whisparr",
                "prowlarr": "/data/torrents/prowlarr",
                "radarr-imported": "/data/torrents/radarr-imported",
                "tv-sonarr-imported": "/data/torrents/tv-sonarr-imported",
                "lidarr-imported": "/data/torrents/lidarr-imported",
                "whisparr-imported": "/data/torrents/whisparr-imported",
            },
        )

    def test_qbittorrent_categories_state_reads_save_paths(self) -> None:
        with mock.patch.object(
            haac,
            "http_request_json",
            return_value={
                "radarr": {"name": "radarr", "savePath": "/data/torrents/radarr/"},
                "tv-sonarr": {"name": "tv-sonarr", "savePath": "/data/torrents/tv-sonarr"},
            },
        ):
            result = haac.qbittorrent_categories_state(8080, opener=object())

        self.assertEqual(
            result,
            {
                "radarr": "/data/torrents/radarr",
                "tv-sonarr": "/data/torrents/tv-sonarr",
            },
        )

    def test_ensure_qbittorrent_app_preferences_reconciles_supported_queue_defaults(self) -> None:
        with mock.patch.object(haac, "qbittorrent_login_via_port_forward", return_value=object()):
            with mock.patch.object(
                haac,
                "qbittorrent_preferences_state",
                side_effect=[
                    {"queueing_enabled": True, "max_active_downloads": 3, "dont_count_slow_torrents": False},
                    dict(haac.QBITTORRENT_APP_PREFERENCE_DEFAULTS),
                ],
            ):
                with mock.patch.object(haac, "http_request_form_text", return_value=(200, "")) as request:
                    result = haac.ensure_qbittorrent_app_preferences(
                        8080,
                        username="admin",
                        password="secret",
                    )

        self.assertEqual(result, haac.QBITTORRENT_APP_PREFERENCE_DEFAULTS)
        self.assertEqual(request.call_args.args[0], "http://127.0.0.1:8080/api/v2/app/setPreferences")
        self.assertIn('"max_active_downloads":8', request.call_args.kwargs["fields"][0][1])

    def test_ensure_qbittorrent_category_paths_creates_and_updates_drifted_categories(self) -> None:
        with mock.patch.object(haac, "qbittorrent_login_via_port_forward", return_value=object()):
            with mock.patch.object(
                haac,
                "qbittorrent_categories_state",
                side_effect=[
                    {
                        "radarr": "/legacy/radarr",
                        "tv-sonarr": "/data/torrents/tv-sonarr",
                    },
                    haac.ARR_QBITTORRENT_CATEGORY_SAVE_PATHS,
                ],
            ):
                with mock.patch.object(haac, "http_request_form_text", return_value=(200, "")) as request:
                    result = haac.ensure_qbittorrent_category_paths(
                        8080,
                        username="admin",
                        password="secret",
                    )

        self.assertEqual(result, haac.ARR_QBITTORRENT_CATEGORY_SAVE_PATHS)
        endpoints = [call.args[0] for call in request.call_args_list]
        self.assertIn("http://127.0.0.1:8080/api/v2/torrents/editCategory", endpoints)
        self.assertIn("http://127.0.0.1:8080/api/v2/torrents/createCategory", endpoints)

    def test_qbittorrent_port_sync_authenticated_script_uses_in_pod_credentials(self) -> None:
        script = haac.qbittorrent_port_sync_authenticated_script("echo ok")

        self.assertIn("printenv QBIT_USER >/tmp/qbit-user.txt", script)
        self.assertIn("printenv QBIT_PASS >/tmp/qbit-pass.txt", script)
        self.assertIn("--data-urlencode username@/tmp/qbit-user.txt", script)
        self.assertIn("--data-urlencode password@/tmp/qbit-pass.txt", script)
        self.assertIn("echo ok", script)

    def test_ensure_qbittorrent_category_paths_in_session_uses_port_sync_container_api(self) -> None:
        with mock.patch.object(
            haac,
            "qbittorrent_categories_state_in_session",
            side_effect=[
                {"radarr": "/legacy/radarr"},
                haac.ARR_QBITTORRENT_CATEGORY_SAVE_PATHS,
            ],
        ):
            with mock.patch.object(haac, "kubectl_exec_stdout", return_value="") as exec_stdout:
                result = haac.ensure_qbittorrent_category_paths_in_session(
                    "kubectl",
                    Path("demo-kubeconfig"),
                    pod_name="downloaders-abc",
                )

        self.assertEqual(result, haac.ARR_QBITTORRENT_CATEGORY_SAVE_PATHS)
        executed_scripts = [call.kwargs["script"] for call in exec_stdout.call_args_list]
        self.assertTrue(any("/api/v2/torrents/editCategory" in script for script in executed_scripts))
        self.assertTrue(any("/api/v2/torrents/createCategory" in script for script in executed_scripts))

    def test_downloaders_bootstrap_succeeded_from_logs_requires_port_sync_steady_state(self) -> None:
        healthy_logs = "\n".join(
            (
                "Waiting for qBittorrent and QUI endpoints...",
                "qBittorrent category routing reconciled.",
                "qBittorrent credentials reconciled. Upserting QUI instance...",
                "QUI instance connectivity test passed.",
                "Bootstrap complete. Starting port-forward sync loop...",
            )
        )
        incomplete_logs = "\n".join(
            (
                "Waiting for qBittorrent and QUI endpoints...",
                "qBittorrent credentials reconciled. Upserting QUI instance...",
            )
        )

        self.assertTrue(haac.downloaders_bootstrap_succeeded_from_logs(healthy_logs))
        self.assertFalse(haac.downloaders_bootstrap_succeeded_from_logs(incomplete_logs))

    def test_detect_vpn_blocker_from_logs_ignores_healthy_gluetun_steady_state(self) -> None:
        logs = "\n".join(
            (
                "2026-04-18T10:00:00Z INFO OpenVPN 2.6.0 x86_64-pc-linux-gnu",
                "2026-04-18T10:00:03Z INFO Initialization Sequence Completed",
                "2026-04-18T10:00:05Z INFO port forwarded is 61123",
            )
        )

        self.assertEqual(haac.detect_vpn_blocker_from_logs(logs), "")

    def test_detect_vpn_blocker_from_logs_reports_real_proton_failure(self) -> None:
        logs = "\n".join(
            (
                "2026-04-18T10:00:00Z ERROR Your credentials might be wrong",
                "2026-04-18T10:00:01Z ERROR make sure you have +pmp included in your subscription",
            )
        )

        blocker = haac.detect_vpn_blocker_from_logs(logs)

        self.assertIn("Your credentials might be wrong", blocker)
        self.assertIn("+pmp", blocker)


class ArgocdRevisionGateTests(unittest.TestCase):
    def test_repo_managed_application_revision_must_match_expected_sha(self) -> None:
        app = {
            "spec": {"source": {"repoURL": "https://github.com/daubog44/arr_setup.git"}},
            "status": {"sync": {"revision": "oldsha"}},
        }

        self.assertFalse(
            haac.repo_managed_argocd_application_revision_current(
                app,
                expected_revision="newsha",
                gitops_repo_url="https://github.com/daubog44/arr_setup.git",
            )
        )
        self.assertTrue(
            haac.repo_managed_argocd_application_revision_current(
                app,
                expected_revision="newsha",
                gitops_repo_url="https://github.com/example/other.git",
            )
        )

    def test_wait_for_argocd_application_refreshes_stale_but_healthy_repo_app(self) -> None:
        stale_app = {
            "spec": {"source": {"repoURL": "https://github.com/daubog44/arr_setup.git"}},
            "status": {
                "sync": {"status": "Synced", "revision": "old-sha"},
                "health": {"status": "Healthy"},
                "operationState": {"phase": ""},
            },
        }
        fresh_app = {
            "spec": {"source": {"repoURL": "https://github.com/daubog44/arr_setup.git"}},
            "status": {
                "sync": {"status": "Synced", "revision": "new-sha"},
                "health": {"status": "Healthy"},
                "operationState": {"phase": ""},
            },
        }

        with mock.patch.object(haac, "wait_for_resource"):
            with mock.patch.object(haac, "kubectl_json", side_effect=[stale_app, fresh_app]):
                with mock.patch.object(haac, "recover_stale_argocd_operation", return_value=False):
                    with mock.patch.object(haac, "recover_stalled_downloaders_rollout", return_value=False):
                        with mock.patch.object(haac, "refresh_argocd_application") as refresh:
                            with mock.patch.object(haac.time, "sleep"):
                                with mock.patch.object(haac.time, "time", side_effect=[0, 0, 1]):
                                    haac.wait_for_argocd_application_ready(
                                        "kubectl",
                                        Path("demo-kubeconfig"),
                                        application="haac-platform",
                                        stage_label="Platform root gate",
                                        deadline=60,
                                        expected_revision="new-sha",
                                        gitops_repo_url="https://github.com/daubog44/arr_setup.git",
                                    )

        refresh.assert_called_once_with("kubectl", Path("demo-kubeconfig"), "haac-platform", hard=True)

    def test_wait_for_argocd_application_refreshes_stale_failed_repo_app(self) -> None:
        stale_failed = {
            "spec": {"source": {"repoURL": "https://github.com/daubog44/arr_setup.git"}},
            "status": {
                "sync": {"status": "OutOfSync", "revision": "old-sha"},
                "health": {"status": "Degraded"},
                "operationState": {"phase": "Failed", "message": "old failure"},
            },
        }
        fresh = {
            "spec": {"source": {"repoURL": "https://github.com/daubog44/arr_setup.git"}},
            "status": {
                "sync": {"status": "Synced", "revision": "new-sha"},
                "health": {"status": "Healthy"},
                "operationState": {"phase": ""},
            },
        }

        with mock.patch.object(haac, "wait_for_resource"):
            with mock.patch.object(haac, "kubectl_json", side_effect=[stale_failed, fresh]):
                with mock.patch.object(haac, "recover_stale_argocd_operation", return_value=False):
                    with mock.patch.object(haac, "recover_stalled_downloaders_rollout", return_value=False):
                        with mock.patch.object(haac, "refresh_argocd_application") as refresh:
                            with mock.patch.object(haac.time, "sleep"):
                                with mock.patch.object(haac.time, "time", side_effect=[0, 0, 1]):
                                    haac.wait_for_argocd_application_ready(
                                        "kubectl",
                                        Path("demo-kubeconfig"),
                                        application="haac-platform",
                                        stage_label="Platform root gate",
                                        deadline=60,
                                        expected_revision="new-sha",
                                        gitops_repo_url="https://github.com/daubog44/arr_setup.git",
                                    )

        refresh.assert_called_once_with("kubectl", Path("demo-kubeconfig"), "haac-platform", hard=True)

    def test_recover_missing_hook_stall_recycles_repo_managed_child_application(self) -> None:
        child = {
            "metadata": {
                "name": "kube-prometheus-stack",
                "uid": "uid-before-recycle",
                "annotations": {
                    "argocd.argoproj.io/tracking-id": "haac-platform:argoproj.io/Application:argocd/kube-prometheus-stack"
                },
            },
            "spec": {
                "project": "platform",
                "destination": {"namespace": "monitoring"},
                "source": {"repoURL": "https://prometheus-community.github.io/helm-charts"},
            },
            "status": {
                "sync": {"revision": "same-sha"},
                "operationState": {
                    "phase": "Running",
                    "message": "waiting for completion of hook batch/Job/kube-prometheus-stack-admission-create",
                },
            },
            "operation": {"sync": {"revision": "same-sha"}},
        }
        parent = {
            "metadata": {"name": "haac-platform"},
            "spec": {"source": {"repoURL": "https://github.com/daubog44/arr_setup.git"}},
            "status": {"resources": [{"group": "argoproj.io", "kind": "Application", "namespace": "argocd", "name": "kube-prometheus-stack"}]},
        }

        with mock.patch.object(haac, "argocd_hook_resource_exists", return_value=False):
            with mock.patch.object(haac, "kubectl_json", return_value=parent):
                with mock.patch.object(haac, "refresh_argocd_application") as refresh:
                    with mock.patch.object(haac, "wait_for_argocd_application_recreation") as wait:
                        with mock.patch.object(haac, "run") as run:
                            with mock.patch.object(haac, "seconds_remaining", return_value=180):
                                healed = haac.recover_missing_hook_argocd_operation(
                                    "kubectl",
                                    Path("demo-kubeconfig"),
                                    "kube-prometheus-stack",
                                    child,
                                    deadline=180,
                                    gitops_repo_url="https://github.com/daubog44/arr_setup.git",
                                )

        self.assertTrue(healed)
        refresh.assert_called_once_with("kubectl", Path("demo-kubeconfig"), "haac-platform", hard=True)
        wait.assert_called_once_with(
            "kubectl",
            Path("demo-kubeconfig"),
            "kube-prometheus-stack",
            original_uid="uid-before-recycle",
            timeout_seconds=180,
        )
        delete_call = run.call_args.args[0]
        self.assertEqual(delete_call[:7], ["kubectl", "--kubeconfig", "demo-kubeconfig", "delete", "application", "kube-prometheus-stack", "-n"])

    def test_recover_missing_hook_stall_requires_repo_managed_parent(self) -> None:
        child = {
            "metadata": {
                "name": "foreign-app",
                "annotations": {"argocd.argoproj.io/tracking-id": "some-parent:argoproj.io/Application:argocd/foreign-app"},
            },
            "spec": {"destination": {"namespace": "foreign"}},
            "status": {
                "sync": {"revision": "same-sha"},
                "operationState": {
                    "phase": "Running",
                    "message": "waiting for completion of hook batch/Job/foreign-hook",
                },
            },
            "operation": {"sync": {"revision": "same-sha"}},
        }
        parent = {"spec": {"source": {"repoURL": "https://charts.example.invalid"}}}

        with mock.patch.object(haac, "argocd_hook_resource_exists", return_value=False):
            with mock.patch.object(haac, "kubectl_json", return_value=parent):
                with mock.patch.object(haac, "seconds_remaining", return_value=180):
                    with self.assertRaisesRegex(haac.HaaCError, "Manual intervention is required"):
                        haac.recover_missing_hook_argocd_operation(
                            "kubectl",
                            Path("demo-kubeconfig"),
                            "foreign-app",
                            child,
                            deadline=180,
                            gitops_repo_url="https://github.com/daubog44/arr_setup.git",
                        )

    def test_recover_missing_hook_stall_requires_parent_ownership_proof(self) -> None:
        child = {
            "metadata": {
                "name": "kube-prometheus-stack",
                "uid": "uid-before-recycle",
                "annotations": {
                    "argocd.argoproj.io/tracking-id": "haac-platform:argoproj.io/Application:argocd/kube-prometheus-stack"
                },
            },
            "spec": {"destination": {"namespace": "monitoring"}},
            "status": {
                "sync": {"revision": "same-sha"},
                "operationState": {
                    "phase": "Running",
                    "message": "waiting for completion of hook batch/Job/kube-prometheus-stack-admission-create",
                },
            },
            "operation": {"sync": {"revision": "same-sha"}},
        }
        parent = {"spec": {"source": {"repoURL": "https://github.com/daubog44/arr_setup.git"}}, "status": {"resources": []}}

        with mock.patch.object(haac, "argocd_hook_resource_exists", return_value=False):
            with mock.patch.object(haac, "kubectl_json", return_value=parent):
                with mock.patch.object(haac, "seconds_remaining", return_value=180):
                    with self.assertRaisesRegex(haac.HaaCError, "prove ownership"):
                        haac.recover_missing_hook_argocd_operation(
                            "kubectl",
                            Path("demo-kubeconfig"),
                            "kube-prometheus-stack",
                            child,
                            deadline=180,
                            gitops_repo_url="https://github.com/daubog44/arr_setup.git",
                        )

    def test_recover_missing_hook_stall_refuses_child_with_resource_finalizer_variant(self) -> None:
        child = {
            "metadata": {
                "name": "haac-stack",
                "uid": "uid-before-recycle",
                "annotations": {"argocd.argoproj.io/tracking-id": "haac-workloads:argoproj.io/Application:argocd/haac-stack"},
                "finalizers": ["resources-finalizer.argocd.argoproj.io/background"],
            },
            "spec": {"destination": {"namespace": "media"}},
            "status": {
                "sync": {"revision": "same-sha"},
                "operationState": {
                    "phase": "Running",
                    "message": "waiting for completion of hook batch/Job/haac-stack-bootstrap",
                },
            },
            "operation": {"sync": {"revision": "same-sha"}},
        }
        parent = {
            "spec": {"source": {"repoURL": "https://github.com/daubog44/arr_setup.git"}},
            "status": {"resources": [{"group": "argoproj.io", "kind": "Application", "namespace": "argocd", "name": "haac-stack"}]},
        }

        with mock.patch.object(haac, "argocd_hook_resource_exists", return_value=False):
            with mock.patch.object(haac, "kubectl_json", return_value=parent):
                with mock.patch.object(haac, "seconds_remaining", return_value=180):
                    with self.assertRaisesRegex(haac.HaaCError, "resources finalizer"):
                        haac.recover_missing_hook_argocd_operation(
                            "kubectl",
                            Path("demo-kubeconfig"),
                            "haac-stack",
                            child,
                            deadline=180,
                            gitops_repo_url="https://github.com/daubog44/arr_setup.git",
                        )

    def test_wait_for_argocd_application_recreation_requires_uid_change(self) -> None:
        responses = [
            mock.Mock(returncode=0, stdout='{"metadata":{"uid":"uid-before-recycle"}}'),
            mock.Mock(returncode=0, stdout='{"metadata":{"uid":"uid-before-recycle","deletionTimestamp":"2026-04-19T16:00:00Z"}}'),
            mock.Mock(returncode=0, stdout='{"metadata":{"uid":"uid-after-recycle"}}'),
        ]
        with mock.patch.object(haac, "run", side_effect=responses):
            with mock.patch.object(haac.time, "sleep"):
                with mock.patch.object(haac.time, "time", side_effect=[0, 0, 1, 2]):
                    haac.wait_for_argocd_application_recreation(
                        "kubectl",
                        Path("demo-kubeconfig"),
                        "kube-prometheus-stack",
                        original_uid="uid-before-recycle",
                        timeout_seconds=10,
                        interval_seconds=1,
                    )

    def test_sync_argocd_application_patches_operation_sync(self) -> None:
        with mock.patch.object(haac, "run") as run:
            haac.sync_argocd_application("kubectl", Path("demo-kubeconfig"), "policy-reporter")

        command = run.call_args.args[0]
        payload = json.loads(command[-1])
        self.assertEqual(
            command[:-1],
            [
                "kubectl",
                "--kubeconfig",
                "demo-kubeconfig",
                "patch",
                "application",
                "policy-reporter",
                "-n",
                "argocd",
                "--type",
                "merge",
                "--patch",
            ],
        )
        self.assertEqual(payload["operation"]["initiatedBy"]["username"], "haac")
        self.assertEqual(payload["operation"]["sync"]["syncStrategy"], {"hook": {}})

    def test_recover_missing_api_resource_restarts_sync_once_crd_exists(self) -> None:
        app = {
            "status": {
                "operationState": {
                    "message": (
                        'one or more synchronization tasks completed unsuccessfully, reason: '
                        'resource mapping not found for name: "policy-reporter-monitoring" namespace: "security" '
                        'from "/tmp/demo": no matches for kind "ServiceMonitor" in version '
                        '"monitoring.coreos.com/v1" ensure CRDs are installed first'
                    )
                }
            }
        }

        with mock.patch.object(haac, "monitoring_servicemonitor_crd_available", return_value=True):
            with mock.patch.object(haac, "refresh_argocd_application") as refresh:
                with mock.patch.object(haac, "sync_argocd_application") as sync:
                    healed = haac.recover_missing_api_resource_argocd_operation(
                        "kubectl",
                        Path("demo-kubeconfig"),
                        "policy-reporter",
                        app,
                    )

        self.assertTrue(healed)
        refresh.assert_called_once_with("kubectl", Path("demo-kubeconfig"), "policy-reporter", hard=True)
        sync.assert_called_once_with("kubectl", Path("demo-kubeconfig"), "policy-reporter")


class ArrStackSurfaceTests(unittest.TestCase):
    def test_up_task_phases_include_media_post_install(self) -> None:
        self.assertEqual(haac.UP_TASK_PHASES["media:post-install"], "GitOps readiness")

    def test_arr_ping_success_pattern_accepts_ok_json_and_legacy_pong(self) -> None:
        self.assertRegex('{\n  "status": "OK"\n}', haac.ARR_PING_SUCCESS_PATTERN)
        self.assertRegex("pong", haac.ARR_PING_SUCCESS_PATTERN)
        self.assertNotRegex('{"status":"ERROR"}', haac.ARR_PING_SUCCESS_PATTERN)

    def test_seerr_login_with_jellyfin_uses_internal_service_payload(self) -> None:
        opener = object()
        with mock.patch.object(haac, "build_cookie_opener", return_value=opener):
            with mock.patch.object(haac, "http_request_text", return_value=(200, "{}")) as request:
                result = haac.seerr_login_with_jellyfin(
                    5055,
                    username="jf-admin",
                    password="secret-pass",
                    email="jf@example.com",
                )

        payload = request.call_args.kwargs["payload"]

        self.assertIs(result, opener)
        self.assertEqual(payload["hostname"], haac.SEERR_JELLYFIN_INTERNAL_HOST)
        self.assertEqual(payload["port"], haac.SEERR_JELLYFIN_INTERNAL_PORT)
        self.assertEqual(payload["serverType"], haac.SEERR_JELLYFIN_SERVER_TYPE)
        self.assertFalse(payload["useSsl"])
        self.assertEqual(payload["urlBase"], "")

    def test_seerr_login_with_jellyfin_omits_server_details_on_rerun(self) -> None:
        opener = object()
        with mock.patch.object(haac, "build_cookie_opener", return_value=opener):
            with mock.patch.object(haac, "http_request_text", return_value=(200, "{}")) as request:
                result = haac.seerr_login_with_jellyfin(
                    5055,
                    username="jf-admin",
                    password="secret-pass",
                    email="jf@example.com",
                    public_settings={"mediaServerType": haac.SEERR_JELLYFIN_SERVER_TYPE},
                )

        payload = request.call_args.kwargs["payload"]

        self.assertIs(result, opener)
        self.assertEqual(payload["username"], "jf-admin")
        self.assertEqual(payload["password"], "secret-pass")
        self.assertEqual(payload["email"], "jf@example.com")
        self.assertNotIn("hostname", payload)
        self.assertNotIn("port", payload)
        self.assertNotIn("useSsl", payload)
        self.assertNotIn("urlBase", payload)
        self.assertNotIn("serverType", payload)

    def test_ensure_seerr_main_settings_persists_public_application_url(self) -> None:
        opener = object()
        with mock.patch.object(
            haac,
            "http_request_json",
            side_effect=[
                {"applicationTitle": "Seerr", "applicationUrl": ""},
                {"applicationTitle": "Seerr", "applicationUrl": "https://seerr.example.com"},
                {"applicationTitle": "Seerr", "applicationUrl": "https://seerr.example.com"},
            ],
        ) as request_json:
            result = haac.ensure_seerr_main_settings(opener, 5055, domain_name="example.com")

        payload = request_json.call_args_list[1].kwargs["payload"]
        self.assertEqual(payload, {"applicationUrl": "https://seerr.example.com"})
        self.assertEqual(payload["applicationUrl"], "https://seerr.example.com")
        self.assertEqual(result["applicationUrl"], "https://seerr.example.com")

    def test_jellyfin_startup_incomplete_uses_public_info_flag(self) -> None:
        self.assertTrue(haac.jellyfin_startup_incomplete({"StartupWizardCompleted": False}))
        self.assertFalse(haac.jellyfin_startup_incomplete({"StartupWizardCompleted": True}))

    def test_jellyfin_auth_headers_include_access_token(self) -> None:
        headers = haac.jellyfin_auth_headers("demo-token")

        self.assertIn("Authorization", headers)
        self.assertIn("Token=demo-token", headers["Authorization"])

    def test_qbittorrent_webui_headers_force_managed_host_header(self) -> None:
        headers = haac.qbittorrent_webui_headers()

        self.assertEqual(headers["Host"], haac.QBITTORRENT_WEBUI_HOST_HEADER)
        self.assertEqual(headers["Referer"], f"http://{haac.QBITTORRENT_WEBUI_HOST_HEADER}/")

    def test_prowlarr_baseline_indexers_include_public_movie_and_tv_sources(self) -> None:
        self.assertEqual(
            tuple(item["name"] for item in haac.PROWLARR_BASELINE_INDEXERS),
            ("YTS", "1337x"),
        )
        self.assertEqual(haac.PROWLARR_BASELINE_INDEXERS[1]["tags"], ("flaresolverr",))

    def test_arr_verifier_candidates_use_curated_public_domain_smoke_titles(self) -> None:
        self.assertEqual(
            tuple(item["title"] for item in haac.ARR_VERIFIER_CANDIDATES),
            (
                "Metropolis",
                "Charade",
                "Carnival of Souls",
                "The Last Man on Earth",
                "The Cabinet of Dr. Caligari",
            ),
        )

    def test_default_prowlarr_app_profile_id_prefers_standard(self) -> None:
        with mock.patch.object(
            haac,
            "http_request_json",
            return_value=[
                {"id": 2, "name": "Secondary"},
                {"id": 1, "name": "Standard"},
            ],
        ):
            profile_id = haac.default_prowlarr_app_profile_id(9696, api_key="api-key")

        self.assertEqual(profile_id, 1)

    def test_ensure_prowlarr_flaresolverr_proxy_creates_tagged_proxy(self) -> None:
        schema_item = {
            "implementation": "FlareSolverr",
            "fields": [
                {"name": "host", "value": "http://localhost:8191/"},
                {"name": "requestTimeout", "value": 60},
            ],
            "tags": [],
        }
        configured_proxy = {
            "implementation": "FlareSolverr",
            "fields": [
                {"name": "host", "value": haac.FLARESOLVERR_INTERNAL_URL},
                {"name": "requestTimeout", "value": 60},
            ],
            "tags": [1],
        }
        with mock.patch.object(
            haac,
            "http_request_json",
            side_effect=[
                [],
                [{"label": "flaresolverr", "id": 1}],
                [],
                [schema_item],
                [configured_proxy],
            ],
        ):
            with mock.patch.object(haac, "http_request_text", side_effect=[(201, "{}"), (201, "{}")]) as request_text:
                result = haac.ensure_prowlarr_flaresolverr_proxy(9696, api_key="api-key")

        first_payload = request_text.call_args_list[0].kwargs["payload"]
        second_payload = request_text.call_args_list[1].kwargs["payload"]
        self.assertEqual(first_payload, {"label": "flaresolverr"})
        self.assertEqual(second_payload["name"], "FlareSolverr")
        self.assertEqual(second_payload["tags"], [1])
        self.assertEqual(haac.field_value(second_payload["fields"], "host"), haac.FLARESOLVERR_INTERNAL_URL)
        self.assertEqual(result[0]["implementation"], "FlareSolverr")

    def test_ensure_prowlarr_indexer_uses_schema_name_and_magnet_preference(self) -> None:
        schema_item = {
            "name": "YTS",
            "indexerUrls": ["https://yts.bz/"],
            "appProfileId": 0,
            "fields": [
                {"name": "baseUrl"},
                {"name": "torrentBaseSettings.preferMagnetUrl", "value": False},
            ],
        }
        configured_item = {
            "name": "YTS",
            "appProfileId": 1,
            "tags": [7],
            "fields": [
                {"name": "baseUrl", "value": "https://yts.bz/"},
                {"name": "torrentBaseSettings.preferMagnetUrl", "value": True},
            ],
        }
        with mock.patch.object(
            haac,
            "http_request_json",
            side_effect=[
                [],
                [{"id": 1, "name": "Standard"}],
                [],
                [{"label": "flaresolverr", "id": 7}],
                [schema_item],
                [configured_item],
            ],
        ):
            with mock.patch.object(haac, "http_request_text", return_value=(201, "{}")) as request_text:
                result = haac.ensure_prowlarr_indexer(
                    9696,
                    api_key="api-key",
                    name="YTS",
                    tag_labels=("flaresolverr",),
                )

        payload = request_text.call_args.kwargs["payload"]
        self.assertEqual(result[0]["name"], "YTS")
        self.assertEqual(payload["name"], "YTS")
        self.assertEqual(payload["appProfileId"], 1)
        self.assertEqual(payload["tags"], [7])
        self.assertTrue(haac.field_value(payload["fields"], "torrentBaseSettings.preferMagnetUrl"))
        self.assertEqual(haac.field_value(payload["fields"], "baseUrl"), "https://yts.bz/")

    def test_run_prowlarr_command_posts_requested_name(self) -> None:
        with mock.patch.object(haac, "http_request_json", return_value={"name": "ApplicationIndexerSync"}) as request_json:
            result = haac.run_prowlarr_command(9696, api_key="api-key", name="ApplicationIndexerSync")

        self.assertEqual(result["name"], "ApplicationIndexerSync")
        self.assertEqual(request_json.call_args.kwargs["payload"], {"name": "ApplicationIndexerSync"})

    def test_trigger_radarr_release_download_injects_movie_id_when_missing(self) -> None:
        release = {"guid": "release-guid", "indexerId": 2}
        with mock.patch.object(haac, "http_request_json", return_value={"ok": True}) as request_json:
            result = haac.trigger_radarr_release_download(7878, api_key="radarr-key", release=release, movie_id=42)

        self.assertEqual(result, {"ok": True})
        self.assertEqual(request_json.call_args.kwargs["payload"]["movieId"], 42)
        self.assertEqual(request_json.call_args.kwargs["payload"]["guid"], "release-guid")

    def test_exact_seeded_prowlarr_releases_prefers_small_seeded_exact_title_year(self) -> None:
        results = [
            {"title": "The General (1926) [1080p] [BluRay] [YTS] [YIFY]", "size": 1713691904, "seeders": 96},
            {"title": "The General (1926) [720p] [BluRay] [YTS] [YIFY]", "size": 768198720, "seeders": 114},
            {"title": "Berlin: Symphony of a Metropolis (1927) [720p] [BluRay] [YTS] [YIFY]", "size": 564800768, "seeders": 36},
            {"title": "The.General.1926.REMASTERED.720p.BluRay.999MB.HQ.x265.10bit GalaxyRG ⭐", "size": 1032963776, "seeders": 11},
            {"title": "The General (1926) [720p] [BluRay] [YTS] [YIFY]", "size": 768198720, "seeders": 0},
        ]

        matches = haac.exact_seeded_prowlarr_releases(results, candidate_title="The General", year=1926)

        self.assertEqual([item["title"] for item in matches], [
            "The.General.1926.REMASTERED.720p.BluRay.999MB.HQ.x265.10bit GalaxyRG ⭐",
            "The General (1926) [720p] [BluRay] [YTS] [YIFY]",
            "The General (1926) [1080p] [BluRay] [YTS] [YIFY]",
        ])

    def test_exact_jellyfin_movie_match_accepts_localized_title_when_year_and_path_match(self) -> None:
        items = [
            {
                "Name": "L'ultimo uomo della Terra",
                "ProductionYear": 1964,
                "Path": "/data/movies/The Last Man on Earth (1964)/The Last Man on Earth (1964) {imdb-tt0058700} [WEBRip-720p][Opus 2.0][x265]-budgetbits.mkv",
            }
        ]

        match = haac.exact_jellyfin_movie_match(
            items,
            title="The Last Man on Earth",
            year=1964,
            imported_file_path="/data/movies/The Last Man on Earth (1964)/The Last Man on Earth (1964) {imdb-tt0058700} [WEBRip-720p][Opus 2.0][x265]-budgetbits.mkv",
        )

        self.assertEqual(match["Name"], "L'ultimo uomo della Terra")

    def test_arr_verifier_candidate_rank_prefers_fresh_title_over_stale_existing_movie(self) -> None:
        fresh_rank = haac.arr_verifier_candidate_rank(
            {},
            [{"title": "Night of the Living Dead (1968) [BluRay] [720p] [YTS] [YIFY]", "size": 828855296, "seeders": 58}],
        )
        stale_rank = haac.arr_verifier_candidate_rank(
            {"id": 2, "hasFile": False},
            [{"title": "The General (1926) [720p] [BluRay] [YTS] [YIFY]", "size": 768198720, "seeders": 114}],
        )

        self.assertLess(fresh_rank, stale_rank)

    def test_arr_verifier_candidate_rank_prefers_imported_title_over_fresh_candidate(self) -> None:
        imported_rank = haac.arr_verifier_candidate_rank(
            {"id": 6, "hasFile": True},
            [{"title": "Nosferatu A Symphony of Horror 1922 Tinted 1080p BluRay HEVC x265 5.1 BONE", "size": 1673963520, "seeders": 59}],
        )
        fresh_rank = haac.arr_verifier_candidate_rank(
            {},
            [{"title": "Night.of.the.Living.Dead.1968.REMASTERED.REPACK.720p.BluRay.999MB.HQ.x265.10bit GalaxyRG ⭐", "size": 1048172288, "seeders": 15}],
        )

        self.assertLess(imported_rank, fresh_rank)

    def test_arr_verifier_candidate_rank_deprioritizes_titles_only_present_in_jellyfin(self) -> None:
        fresh_rank = haac.arr_verifier_candidate_rank(
            {},
            [{"title": "Night of the Living Dead (1968) [BluRay] [720p] [YTS] [YIFY]", "size": 828855296, "seeders": 58}],
        )
        stale_library_rank = haac.arr_verifier_candidate_rank(
            {},
            [{"title": "Nosferatu A Symphony of Horror 1922 Tinted 1080p BluRay HEVC x265 5.1 BONE", "size": 1673963520, "seeders": 59}],
            seerr_match={
                "mediaInfo": {
                    "jellyfinMediaId": "006091dbf4b87956147ce22c93581932",
                    "mediaUrl": "https://jellyfin.example/web/#/details?id=006091dbf4b87956147ce22c93581932",
                }
            },
        )

        self.assertLess(fresh_rank, stale_library_rank)

    def test_arr_verifier_candidate_rank_prefers_smaller_smoke_candidate_once_size_is_acceptable(self) -> None:
        smaller_rank = haac.arr_verifier_candidate_rank(
            {},
            [{"title": "The Last Man on Earth (1964) 720p", "size": 315_118_048, "seeders": 20}],
        )
        larger_rank = haac.arr_verifier_candidate_rank(
            {},
            [{"title": "Metropolis (1927) 1080p", "size": 1_514_190_720, "seeders": 102}],
        )

        self.assertLess(smaller_rank, larger_rank)

    def test_preferred_arr_verifier_release_prefers_download_allowed_small_release(self) -> None:
        releases = [
            {"title": "Large OK", "size": 6_850_472_960, "seeders": 8, "downloadAllowed": True},
            {"title": "Small OK", "size": 768_198_720, "seeders": 114, "downloadAllowed": True},
            {"title": "Blocked Small", "size": 735_072_768, "seeders": 2, "downloadAllowed": False},
        ]

        preferred = haac.preferred_arr_verifier_release(releases)

        self.assertEqual(preferred["title"], "Small OK")

    def test_preferred_arr_verifier_release_prefers_approved_release_over_rejected_small_one(self) -> None:
        releases = [
            {
                "title": "Night.of.the.Living.Dead.1968.REMASTERED.REPACK.720p.BluRay.999MB.HQ.x265.10bit GalaxyRG",
                "size": 1_048_172_288,
                "seeders": 15,
                "downloadAllowed": True,
                "approved": False,
                "rejected": True,
                "temporarilyRejected": False,
                "rejections": ["999.6 MB is smaller than minimum allowed 2.4 GB"],
            },
            {
                "title": "Night of the Living Dead 1968 4K SDR 2160p BDRemux Ita Eng x265-NAHOM",
                "size": 58_765_889_536,
                "seeders": 3,
                "downloadAllowed": True,
                "approved": True,
                "rejected": False,
                "temporarilyRejected": False,
                "rejections": [],
            },
        ]

        preferred = haac.preferred_arr_verifier_release(releases)

        self.assertEqual(preferred["title"], "Night of the Living Dead 1968 4K SDR 2160p BDRemux Ita Eng x265-NAHOM")

    def test_console_safe_text_replaces_unencodable_console_characters(self) -> None:
        fake_stdout = type("FakeStdout", (), {"encoding": "cp1252"})()
        with mock.patch.object(haac.sys, "stdout", fake_stdout):
            safe_text = haac.console_safe_text("GalaxyRG ⭐")

        self.assertEqual(safe_text, "GalaxyRG ?")

    def test_torrent_matches_selected_release_prefers_download_id_hash(self) -> None:
        torrent = {"name": "Metropolis (Restored)", "hash": "7782ab24188091eae3f61fd218b2dffb4bf9cf9c"}

        self.assertTrue(
            haac.torrent_matches_selected_release(
                torrent,
                selected_title="Metropolis (Restored)(1927) MP 4 [Dascubadude]",
                selected_download_id="7782AB24188091EAE3F61FD218B2DFFB4BF9CF9C",
            )
        )

    def test_torrent_matches_selected_release_falls_back_to_normalized_name_overlap(self) -> None:
        torrent = {"name": "Metropolis (Restored)"}

        self.assertTrue(
            haac.torrent_matches_selected_release(
                torrent,
                selected_title="Metropolis (Restored)(1927) MP 4 [Dascubadude]",
            )
        )

    def test_qbittorrent_cleanup_arr_verifier_artifacts_only_targets_incomplete_smoke_titles(self) -> None:
        torrents = [
            {"name": "Metropolis (Restored)", "hash": "AAA", "category": "radarr", "progress": 0.25},
            {"name": "Normal User Download", "hash": "BBB", "category": "radarr", "progress": 0.10},
            {"name": "Charade", "hash": "CCC", "category": "radarr-imported", "progress": 0.10},
            {"name": "Carnival of Souls", "hash": "DDD", "category": "radarr", "progress": 1.0},
        ]
        with mock.patch.object(haac, "qbittorrent_torrents_info", return_value=torrents):
            with mock.patch.object(haac, "qbittorrent_delete_torrents") as delete_torrents:
                removed = haac.qbittorrent_cleanup_arr_verifier_artifacts(8080, opener=object())

        self.assertEqual(removed, 1)
        self.assertEqual(delete_torrents.call_args.kwargs["hashes"], ["AAA"])
        self.assertTrue(delete_torrents.call_args.kwargs["delete_files"])

    def test_container_media_path_to_host_nas_path_maps_data_root(self) -> None:
        host_path = haac.container_media_path_to_host_nas_path(
            "/data/media/movies/The General (1926)/The General (1926).mkv",
            host_nas_path="/mnt/pve/zima",
        )

        self.assertEqual(str(host_path), "/mnt/pve/zima/media/movies/The General (1926)/The General (1926).mkv")

    def test_arr_verifier_failure_formats_blocker_and_stage(self) -> None:
        with self.assertRaisesRegex(haac.HaaCError, "Furthest verified stage: qBittorrent handoff"):
            haac.arr_verifier_failure(
                furthest_verified="qBittorrent handoff",
                blocker="downloader/VPN drift",
                detail="demo detail",
            )

    def test_ensure_arr_root_folder_creates_missing_path(self) -> None:
        with mock.patch.object(
            haac,
            "http_request_json",
            side_effect=[[], [{"path": haac.ARR_DEFAULT_ROOT_FOLDERS["radarr"], "id": 1}]],
        ) as request_json:
            with mock.patch.object(haac, "http_request_text", return_value=(201, '{"id":1}')) as request_text:
                result = haac.ensure_arr_root_folder(
                    7878,
                    app_name="Radarr",
                    api_key="api-key",
                    path=haac.ARR_DEFAULT_ROOT_FOLDERS["radarr"],
                )

        self.assertEqual(result[0]["path"], haac.ARR_DEFAULT_ROOT_FOLDERS["radarr"])
        self.assertEqual(request_json.call_count, 2)
        self.assertEqual(request_text.call_args.kwargs["payload"], {"path": haac.ARR_DEFAULT_ROOT_FOLDERS["radarr"]})

    def test_ensure_arr_root_folder_noops_when_path_exists(self) -> None:
        existing = [{"path": haac.ARR_DEFAULT_ROOT_FOLDERS["sonarr"], "id": 1}]
        with mock.patch.object(haac, "http_request_json", return_value=existing) as request_json:
            with mock.patch.object(haac, "http_request_text") as request_text:
                result = haac.ensure_arr_root_folder(
                    8989,
                    app_name="Sonarr",
                    api_key="api-key",
                    path=haac.ARR_DEFAULT_ROOT_FOLDERS["sonarr"],
                )

        self.assertEqual(result, existing)
        self.assertEqual(request_json.call_count, 1)
        request_text.assert_not_called()

    def test_ensure_arr_root_folder_supports_lidarr_api_v1(self) -> None:
        with mock.patch.object(
            haac,
            "http_request_json",
            side_effect=[
                [],
                [{"id": 7, "name": "Any"}],
                [{"id": 9, "name": "Standard"}],
                [{"path": haac.ARR_DEFAULT_ROOT_FOLDERS["lidarr"], "id": 1}],
            ],
        ) as request_json:
            with mock.patch.object(haac, "http_request_text", return_value=(201, '{"id":1}')) as request_text:
                result = haac.ensure_arr_root_folder(
                    8686,
                    app_name="Lidarr",
                    api_key="api-key",
                    path=haac.ARR_DEFAULT_ROOT_FOLDERS["lidarr"],
                    api_version="v1",
                )

        self.assertEqual(result[0]["path"], haac.ARR_DEFAULT_ROOT_FOLDERS["lidarr"])
        self.assertIn("/api/v1/rootfolder", request_text.call_args.args[0])
        self.assertIn("/api/v1/rootfolder", request_json.call_args_list[0].args[0])
        self.assertIn("/api/v1/qualityprofile", request_json.call_args_list[1].args[0])
        self.assertIn("/api/v1/metadataprofile", request_json.call_args_list[2].args[0])
        self.assertEqual(
            request_text.call_args.kwargs["payload"],
            {
                "name": "Music",
                "path": haac.ARR_DEFAULT_ROOT_FOLDERS["lidarr"],
                "defaultQualityProfileId": 7,
                "defaultMetadataProfileId": 9,
                "defaultTags": [],
            },
        )

    def test_ensure_arr_qbittorrent_download_client_creates_missing_radarr_client(self) -> None:
        schema_item = {
            "implementation": "QBittorrent",
            "implementationName": "qBittorrent",
            "name": "",
            "fields": [
                {"name": "host", "value": "localhost"},
                {"name": "port", "value": 8080},
                {"name": "username", "value": None},
                {"name": "password", "value": None},
                {"name": "movieCategory", "value": "radarr"},
                {"name": "movieImportedCategory", "value": None},
            ],
        }
        final = [
            {
                "id": 1,
                "implementation": "QBittorrent",
                "name": haac.ARR_QBITTORRENT_CLIENT_NAME,
                "fields": [
                    {"name": "host", "value": haac.QBITTORRENT_INTERNAL_HOST},
                    {"name": "port", "value": haac.QBITTORRENT_INTERNAL_PORT},
                    {"name": "username", "value": "admin"},
                    {"name": "password", "value": "********"},
                    {"name": "movieCategory", "value": haac.ARR_QBITTORRENT_CATEGORIES["radarr"]},
                    {"name": "movieImportedCategory", "value": haac.ARR_QBITTORRENT_IMPORTED_CATEGORIES["radarr"]},
                ],
            }
        ]
        with mock.patch.object(haac, "http_request_json", side_effect=[[], [schema_item], final]) as request_json:
            with mock.patch.object(haac, "http_request_text", side_effect=[(200, "{}"), (201, '{"id":1}')]) as request_text:
                result = haac.ensure_arr_qbittorrent_download_client(
                    7878,
                    app_name="Radarr",
                    api_key="api-key",
                    username="admin",
                    password="secret",
                )

        self.assertEqual(result, final)
        self.assertTrue(request_text.call_args_list[0].args[0].endswith("/api/v3/downloadclient/test"))
        payload = request_text.call_args_list[1].kwargs["payload"]
        self.assertEqual(payload["name"], haac.ARR_QBITTORRENT_CLIENT_NAME)
        fields = payload["fields"]
        self.assertEqual(haac.field_value(fields, "host"), haac.QBITTORRENT_INTERNAL_HOST)
        self.assertEqual(haac.field_value(fields, "username"), "admin")
        self.assertEqual(haac.field_value(fields, "movieImportedCategory"), haac.ARR_QBITTORRENT_IMPORTED_CATEGORIES["radarr"])
        self.assertEqual(request_json.call_count, 3)

    def test_ensure_arr_qbittorrent_download_client_updates_existing_sonarr_client(self) -> None:
        current = [
            {
                "id": 7,
                "implementation": "QBittorrent",
                "name": "legacy",
                "fields": [
                    {"name": "host", "value": "legacy-host"},
                    {"name": "port", "value": 8080},
                    {"name": "username", "value": "legacy"},
                    {"name": "password", "value": "********"},
                    {"name": "tvCategory", "value": "legacy"},
                    {"name": "tvImportedCategory", "value": None},
                ],
            }
        ]
        final = [
            {
                "id": 7,
                "implementation": "QBittorrent",
                "name": haac.ARR_QBITTORRENT_CLIENT_NAME,
                "fields": [
                    {"name": "host", "value": haac.QBITTORRENT_INTERNAL_HOST},
                    {"name": "port", "value": haac.QBITTORRENT_INTERNAL_PORT},
                    {"name": "username", "value": "admin"},
                    {"name": "password", "value": "********"},
                    {"name": "tvCategory", "value": haac.ARR_QBITTORRENT_CATEGORIES["sonarr"]},
                    {"name": "tvImportedCategory", "value": haac.ARR_QBITTORRENT_IMPORTED_CATEGORIES["sonarr"]},
                ],
            }
        ]
        with mock.patch.object(haac, "http_request_json", side_effect=[current, final]):
            with mock.patch.object(haac, "http_request_text", side_effect=[(200, "{}"), (202, "{}")]) as request_text:
                result = haac.ensure_arr_qbittorrent_download_client(
                    8989,
                    app_name="Sonarr",
                    api_key="api-key",
                    username="admin",
                    password="secret",
                )

        self.assertEqual(result, final)
        self.assertTrue(request_text.call_args_list[1].args[0].endswith("/api/v3/downloadclient/7"))
        payload = request_text.call_args_list[1].kwargs["payload"]
        self.assertEqual(payload["name"], haac.ARR_QBITTORRENT_CLIENT_NAME)
        self.assertEqual(haac.field_value(payload["fields"], "tvCategory"), haac.ARR_QBITTORRENT_CATEGORIES["sonarr"])

    def test_ensure_arr_qbittorrent_download_client_supports_lidarr_category_field(self) -> None:
        schema_item = {
            "implementation": "QBittorrent",
            "implementationName": "qBittorrent",
            "name": "",
            "fields": [
                {"name": "host", "value": "localhost"},
                {"name": "port", "value": 8080},
                {"name": "username", "value": None},
                {"name": "password", "value": None},
                {"name": "category", "value": "legacy"},
                {"name": "postImportCategory", "value": None},
            ],
        }
        final = [
            {
                "id": 12,
                "implementation": "QBittorrent",
                "name": haac.ARR_QBITTORRENT_CLIENT_NAME,
                "fields": [
                    {"name": "host", "value": haac.QBITTORRENT_INTERNAL_HOST},
                    {"name": "port", "value": haac.QBITTORRENT_INTERNAL_PORT},
                    {"name": "username", "value": "admin"},
                    {"name": "password", "value": "********"},
                    {"name": "category", "value": haac.ARR_QBITTORRENT_CATEGORIES["lidarr"]},
                    {"name": "postImportCategory", "value": haac.ARR_QBITTORRENT_IMPORTED_CATEGORIES["lidarr"]},
                ],
            }
        ]
        with mock.patch.object(haac, "http_request_json", side_effect=[[], [schema_item], final]):
            with mock.patch.object(haac, "http_request_text", side_effect=[(200, "{}"), (201, '{"id":12}')]) as request_text:
                result = haac.ensure_arr_qbittorrent_download_client(
                    8686,
                    app_name="Lidarr",
                    api_key="api-key",
                    username="admin",
                    password="secret",
                    api_version="v1",
                )

        self.assertEqual(result, final)
        payload = request_text.call_args_list[1].kwargs["payload"]
        self.assertEqual(haac.field_value(payload["fields"], "category"), haac.ARR_QBITTORRENT_CATEGORIES["lidarr"])
        self.assertEqual(
            haac.field_value(payload["fields"], "postImportCategory"),
            haac.ARR_QBITTORRENT_IMPORTED_CATEGORIES["lidarr"],
        )
        self.assertTrue(request_text.call_args_list[0].args[0].endswith("/api/v1/downloadclient/test"))

    def test_ensure_arr_qbittorrent_download_client_supports_whisparr_movie_categories(self) -> None:
        schema_item = {
            "implementation": "QBittorrent",
            "implementationName": "qBittorrent",
            "name": "",
            "fields": [
                {"name": "host", "value": "localhost"},
                {"name": "port", "value": 8080},
                {"name": "username", "value": None},
                {"name": "password", "value": None},
                {"name": "movieCategory", "value": "legacy"},
                {"name": "movieImportedCategory", "value": None},
            ],
        }
        final = [
            {
                "id": 16,
                "implementation": "QBittorrent",
                "name": haac.ARR_QBITTORRENT_CLIENT_NAME,
                "fields": [
                    {"name": "host", "value": haac.QBITTORRENT_INTERNAL_HOST},
                    {"name": "port", "value": haac.QBITTORRENT_INTERNAL_PORT},
                    {"name": "username", "value": "admin"},
                    {"name": "password", "value": "********"},
                    {"name": "movieCategory", "value": haac.ARR_QBITTORRENT_CATEGORIES["whisparr"]},
                    {"name": "movieImportedCategory", "value": haac.ARR_QBITTORRENT_IMPORTED_CATEGORIES["whisparr"]},
                ],
            }
        ]
        with mock.patch.object(haac, "http_request_json", side_effect=[[], [schema_item], final]):
            with mock.patch.object(haac, "http_request_text", side_effect=[(200, "{}"), (201, '{"id":16}')]) as request_text:
                result = haac.ensure_arr_qbittorrent_download_client(
                    6969,
                    app_name="Whisparr",
                    api_key="whisparr-key",
                    username="admin",
                    password="secret",
                )

        self.assertEqual(result, final)
        payload = request_text.call_args_list[1].kwargs["payload"]
        self.assertEqual(haac.field_value(payload["fields"], "movieCategory"), haac.ARR_QBITTORRENT_CATEGORIES["whisparr"])
        self.assertEqual(
            haac.field_value(payload["fields"], "movieImportedCategory"),
            haac.ARR_QBITTORRENT_IMPORTED_CATEGORIES["whisparr"],
        )

    def test_ensure_arr_sabnzbd_download_client_creates_missing_lidarr_client(self) -> None:
        schema_item = {
            "implementation": "Sabnzbd",
            "implementationName": "SABnzbd",
            "name": "",
            "fields": [
                {"name": "host", "value": "localhost"},
                {"name": "port", "value": 8080},
                {"name": "apiKey", "value": None},
                {"name": "category", "value": "legacy"},
            ],
        }
        final = [
            {
                "id": 18,
                "implementation": "Sabnzbd",
                "name": haac.ARR_SABNZBD_CLIENT_NAME,
                "fields": [
                    {"name": "host", "value": haac.SABNZBD_INTERNAL_HOST},
                    {"name": "port", "value": haac.SABNZBD_INTERNAL_PORT},
                    {"name": "apiKey", "value": "sab-key"},
                    {"name": "category", "value": haac.ARR_SABNZBD_CATEGORIES["lidarr"]},
                ],
            }
        ]
        with mock.patch.object(haac, "http_request_json", side_effect=[[], [schema_item], final]):
            with mock.patch.object(haac, "http_request_text", side_effect=[(200, "{}"), (201, '{"id":18}')]) as request_text:
                result = haac.ensure_arr_sabnzbd_download_client(
                    8686,
                    app_name="Lidarr",
                    api_key="lidarr-key",
                    sabnzbd_api_key="sab-key",
                    api_version="v1",
                )

        self.assertEqual(result, final)
        payload = request_text.call_args_list[1].kwargs["payload"]
        self.assertEqual(payload["name"], haac.ARR_SABNZBD_CLIENT_NAME)
        self.assertEqual(haac.field_value(payload["fields"], "host"), haac.SABNZBD_INTERNAL_HOST)
        self.assertEqual(haac.field_value(payload["fields"], "category"), haac.ARR_SABNZBD_CATEGORIES["lidarr"])

    def test_ensure_arr_sabnzbd_download_client_supports_whisparr_movie_category(self) -> None:
        schema_item = {
            "implementation": "Sabnzbd",
            "implementationName": "SABnzbd",
            "name": "",
            "fields": [
                {"name": "host", "value": "localhost"},
                {"name": "port", "value": 8080},
                {"name": "apiKey", "value": None},
                {"name": "movieCategory", "value": "legacy"},
            ],
        }
        final = [
            {
                "id": 19,
                "implementation": "Sabnzbd",
                "name": haac.ARR_SABNZBD_CLIENT_NAME,
                "fields": [
                    {"name": "host", "value": haac.SABNZBD_INTERNAL_HOST},
                    {"name": "port", "value": haac.SABNZBD_INTERNAL_PORT},
                    {"name": "apiKey", "value": "sab-key"},
                    {"name": "movieCategory", "value": haac.ARR_SABNZBD_CATEGORIES["whisparr"]},
                ],
            }
        ]
        with mock.patch.object(haac, "http_request_json", side_effect=[[], [schema_item], final]):
            with mock.patch.object(haac, "http_request_text", side_effect=[(200, "{}"), (201, '{"id":19}')]) as request_text:
                result = haac.ensure_arr_sabnzbd_download_client(
                    6969,
                    app_name="Whisparr",
                    api_key="whisparr-key",
                    sabnzbd_api_key="sab-key",
                )

        self.assertEqual(result, final)
        payload = request_text.call_args_list[1].kwargs["payload"]
        self.assertEqual(haac.field_value(payload["fields"], "movieCategory"), haac.ARR_SABNZBD_CATEGORIES["whisparr"])

    def test_ensure_prowlarr_qbittorrent_download_client_creates_missing_client(self) -> None:
        schema_item = {
            "implementation": "QBittorrent",
            "implementationName": "qBittorrent",
            "name": "",
            "fields": [
                {"name": "host", "value": "localhost"},
                {"name": "port", "value": 8080},
                {"name": "username", "value": None},
                {"name": "password", "value": None},
                {"name": "category", "value": "prowlarr"},
            ],
        }
        final = [
            {
                "id": 3,
                "implementation": "QBittorrent",
                "name": haac.ARR_QBITTORRENT_CLIENT_NAME,
                "fields": [
                    {"name": "host", "value": haac.QBITTORRENT_INTERNAL_HOST},
                    {"name": "port", "value": haac.QBITTORRENT_INTERNAL_PORT},
                    {"name": "username", "value": "admin"},
                    {"name": "password", "value": "********"},
                    {"name": "category", "value": haac.ARR_QBITTORRENT_CATEGORIES["prowlarr"]},
                ],
            }
        ]
        with mock.patch.object(haac, "http_request_json", side_effect=[[], [schema_item], final]):
            with mock.patch.object(haac, "http_request_text", return_value=(201, '{"id":3}')) as request_text:
                result = haac.ensure_prowlarr_qbittorrent_download_client(
                    9696,
                    api_key="api-key",
                    username="admin",
                    password="secret",
                )

        self.assertEqual(result, final)
        payload = request_text.call_args.kwargs["payload"]
        self.assertEqual(haac.field_value(payload["fields"], "category"), haac.ARR_QBITTORRENT_CATEGORIES["prowlarr"])

    def test_ensure_prowlarr_sabnzbd_download_client_creates_missing_client(self) -> None:
        schema_item = {
            "implementation": "Sabnzbd",
            "implementationName": "SABnzbd",
            "name": "",
            "fields": [
                {"name": "host", "value": "localhost"},
                {"name": "port", "value": 8080},
                {"name": "apiKey", "value": None},
                {"name": "category", "value": "legacy"},
            ],
        }
        final = [
            {
                "id": 4,
                "implementation": "Sabnzbd",
                "name": haac.ARR_SABNZBD_CLIENT_NAME,
                "fields": [
                    {"name": "host", "value": haac.SABNZBD_INTERNAL_HOST},
                    {"name": "port", "value": haac.SABNZBD_INTERNAL_PORT},
                    {"name": "apiKey", "value": "sab-key"},
                    {"name": "category", "value": haac.ARR_SABNZBD_CATEGORIES["prowlarr"]},
                ],
            }
        ]
        with mock.patch.object(haac, "http_request_json", side_effect=[[], [schema_item], final]):
            with mock.patch.object(haac, "http_request_text", return_value=(201, '{"id":4}')) as request_text:
                result = haac.ensure_prowlarr_sabnzbd_download_client(
                    9696,
                    api_key="prowlarr-key",
                    sabnzbd_api_key="sab-key",
                )

        self.assertEqual(result, final)
        payload = request_text.call_args.kwargs["payload"]
        self.assertEqual(payload["name"], haac.ARR_SABNZBD_CLIENT_NAME)
        self.assertEqual(haac.field_value(payload["fields"], "category"), haac.ARR_SABNZBD_CATEGORIES["prowlarr"])

    def test_ensure_prowlarr_application_updates_existing_sonarr_link(self) -> None:
        current = [
            {
                "id": 11,
                "implementation": "Sonarr",
                "name": "legacy",
                "syncLevel": "fullSync",
                "fields": [
                    {"name": "prowlarrUrl", "value": "http://old-prowlarr"},
                    {"name": "baseUrl", "value": "http://old-sonarr"},
                    {"name": "apiKey", "value": "old-key"},
                ],
            }
        ]
        final = [
            {
                "id": 11,
                "implementation": "Sonarr",
                "name": "Sonarr",
                "syncLevel": "fullSync",
                "fields": [
                    {"name": "prowlarrUrl", "value": haac.PROWLARR_INTERNAL_URL},
                    {"name": "baseUrl", "value": haac.SONARR_INTERNAL_URL},
                    {"name": "apiKey", "value": "new-key"},
                ],
            }
        ]
        with mock.patch.object(haac, "http_request_json", side_effect=[current, final]):
            with mock.patch.object(haac, "http_request_text", return_value=(202, "{}")) as request_text:
                result = haac.ensure_prowlarr_application(
                    9696,
                    api_key="prowlarr-key",
                    implementation="Sonarr",
                    downstream_api_key="new-key",
                    downstream_url=haac.SONARR_INTERNAL_URL,
                )

        self.assertEqual(result, final)
        self.assertTrue(request_text.call_args.args[0].endswith("/api/v1/applications/11"))
        payload = request_text.call_args.kwargs["payload"]
        self.assertEqual(payload["name"], "Sonarr")
        self.assertEqual(haac.field_value(payload["fields"], "prowlarrUrl"), haac.PROWLARR_INTERNAL_URL)
        self.assertEqual(haac.field_value(payload["fields"], "baseUrl"), haac.SONARR_INTERNAL_URL)

    def test_ensure_prowlarr_application_supports_whisparr_link(self) -> None:
        schema_item = {
            "implementation": "Whisparr",
            "name": "",
            "syncLevel": "fullSync",
            "fields": [
                {"name": "prowlarrUrl", "value": ""},
                {"name": "baseUrl", "value": ""},
                {"name": "apiKey", "value": ""},
            ],
        }
        final = [
            {
                "id": 22,
                "implementation": "Whisparr",
                "name": "Whisparr",
                "syncLevel": "fullSync",
                "fields": [
                    {"name": "prowlarrUrl", "value": haac.PROWLARR_INTERNAL_URL},
                    {"name": "baseUrl", "value": haac.WHISPARR_INTERNAL_URL},
                    {"name": "apiKey", "value": "whis-key"},
                ],
            }
        ]
        with mock.patch.object(haac, "http_request_json", side_effect=[[], [schema_item], final]):
            with mock.patch.object(haac, "http_request_text", return_value=(201, '{"id":22}')) as request_text:
                result = haac.ensure_prowlarr_application(
                    9696,
                    api_key="prowlarr-key",
                    implementation="Whisparr",
                    downstream_api_key="whis-key",
                    downstream_url=haac.WHISPARR_INTERNAL_URL,
                )

        self.assertEqual(result, final)
        payload = request_text.call_args.kwargs["payload"]
        self.assertEqual(payload["name"], "Whisparr")
        self.assertEqual(haac.field_value(payload["fields"], "baseUrl"), haac.WHISPARR_INTERNAL_URL)

    def test_recyclarr_runtime_secrets_text_uses_internal_urls(self) -> None:
        content = haac.recyclarr_runtime_secrets_text(radarr_api_key="radarr-key", sonarr_api_key="sonarr-key")

        self.assertIn(f"radarr_main_base_url: {haac.RADARR_INTERNAL_URL}", content)
        self.assertIn("radarr_main_api_key: radarr-key", content)
        self.assertIn(f"sonarr_main_base_url: {haac.SONARR_INTERNAL_URL}", content)
        self.assertIn("sonarr_main_api_key: sonarr-key", content)

    def test_ensure_recyclarr_runtime_secret_applies_stringdata_manifest(self) -> None:
        with mock.patch.object(haac, "run", return_value=mock.Mock(returncode=0, stdout="", stderr="")) as run:
            haac.ensure_recyclarr_runtime_secret(
                "kubectl",
                Path("demo-kubeconfig"),
                radarr_api_key="radarr-key",
                sonarr_api_key="sonarr-key",
                lidarr_api_key="lidarr-key",
                bazarr_api_key="bazarr-key",
                sabnzbd_api_key="sab-key",
            )

        command = run.call_args.args[0]
        manifest = run.call_args.kwargs["input_text"]
        self.assertEqual(command[:4], ["kubectl", "--kubeconfig", "demo-kubeconfig", "apply"])
        self.assertIn("name: recyclarr-secrets", manifest)
        self.assertIn("RADARR_API_KEY: radarr-key", manifest)
        self.assertIn("SONARR_API_KEY: sonarr-key", manifest)
        self.assertIn("LIDARR_API_KEY: lidarr-key", manifest)
        self.assertIn("BAZARR_API_KEY: bazarr-key", manifest)
        self.assertIn("SABNZBD_API_KEY: sab-key", manifest)
        self.assertIn("radarr_main_api_key: radarr-key", manifest)
        self.assertIn("sonarr_main_api_key: sonarr-key", manifest)

    def test_parse_sabnzbd_service_api_key_ignores_preamble(self) -> None:
        result = haac.parse_sabnzbd_service_api_key("__version__ = 19\n[misc]\napi_key = sab-key\n")

        self.assertEqual(result, "sab-key")

    def test_read_bazarr_service_api_key_checks_supported_config_locations(self) -> None:
        with mock.patch.object(haac, "latest_pod_name", return_value="bazarr-pod"):
            with mock.patch.object(haac, "kubectl_exec_stdout", return_value="bazarr-key\n") as exec_stdout:
                result = haac.read_bazarr_service_api_key("kubectl", Path("demo-kubeconfig"))

        self.assertEqual(result, "bazarr-key")
        script = exec_stdout.call_args.kwargs["script"]
        self.assertIn("/config/config/config.yaml", script)
        self.assertIn("/app/config/config.yaml", script)
        self.assertIn("Bazarr config.yaml not found under /config or /app/config", script)

    def test_read_sabnzbd_service_api_key_checks_supported_config_locations(self) -> None:
        with mock.patch.object(haac, "latest_pod_name", return_value="sab-pod"):
            with mock.patch.object(
                haac,
                "kubectl_exec_stdout",
                return_value="__version__ = 19\n[misc]\napi_key = sab-key\n",
            ) as exec_stdout:
                result = haac.read_sabnzbd_service_api_key("kubectl", Path("demo-kubeconfig"))

        self.assertEqual(result, "sab-key")
        script = exec_stdout.call_args.kwargs["script"]
        self.assertIn("/config/sabnzbd.ini", script)
        self.assertIn("SABnzbd sabnzbd.ini not found under /config", script)

    def test_verify_recyclarr_sync_surface_requires_profile_and_custom_formats(self) -> None:
        with mock.patch.object(
            haac,
            "http_request_json",
            side_effect=[
                [{"name": "HD Bluray + WEB"}],
                [{"id": 1, "name": "Preferred Words"}],
            ],
        ):
            haac.verify_recyclarr_sync_surface(
                7878,
                app_name="Radarr",
                api_key="api-key",
                expected_profile="HD Bluray + WEB",
            )

    def test_ensure_seerr_radarr_settings_prefers_test_root_folder_when_present(self) -> None:
        opener = object()
        with mock.patch.object(
            haac,
            "http_request_json",
            side_effect=[
                [],
                {
                    "profiles": [{"id": 4, "name": "HD-1080p"}],
                    "rootFolders": [{"id": 1, "path": "/data/media/movies"}],
                    "tags": [],
                    "urlBase": "",
                },
                {"id": 0},
            ],
        ) as request_json:
            haac.ensure_seerr_radarr_settings(
                opener,
                5055,
                domain_name="example.com",
                radarr_api_key="radarr-key",
                fallback_root_folders=[{"id": 99, "path": "/fallback/movies"}],
            )

        payload = request_json.call_args_list[-1].kwargs["payload"]
        self.assertEqual(payload["activeDirectory"], "/data/media/movies")

    def test_ensure_seerr_sonarr_settings_uses_fallback_root_folder_when_test_is_stale(self) -> None:
        opener = object()
        with mock.patch.object(
            haac,
            "http_request_json",
            side_effect=[
                [],
                {
                    "profiles": [{"id": 4, "name": "HD-1080p"}],
                    "rootFolders": [],
                    "languageProfiles": None,
                    "tags": [],
                    "urlBase": "",
                },
                {"id": 0},
            ],
        ) as request_json:
            haac.ensure_seerr_sonarr_settings(
                opener,
                5055,
                domain_name="example.com",
                sonarr_api_key="sonarr-key",
                fallback_root_folders=[{"id": 1, "path": "/data/media/tv"}],
            )

        payload = request_json.call_args_list[-1].kwargs["payload"]
        self.assertEqual(payload["activeDirectory"], "/data/media/tv")
        self.assertNotIn("activeLanguageProfileId", payload)
        self.assertNotIn("activeAnimeLanguageProfileId", payload)

    def test_ensure_arr_config_fragment_merges_and_verifies_desired_fields(self) -> None:
        with mock.patch.object(
            haac,
            "http_request_json",
            side_effect=[
                {"renameMovies": False, "replaceIllegalCharacters": True, "id": 1},
                {"renameMovies": True, "replaceIllegalCharacters": True, "id": 1},
            ],
        ):
            with mock.patch.object(haac, "http_request_text", return_value=(202, "")) as request:
                result = haac.ensure_arr_config_fragment(
                    7878,
                    app_name="Radarr",
                    api_key="radarr-key",
                    config_name="naming",
                    desired={"renameMovies": True},
                )

        payload = request.call_args.kwargs["payload"]
        self.assertTrue(payload["renameMovies"])
        self.assertTrue(payload["replaceIllegalCharacters"])
        self.assertEqual(payload["id"], 1)
        self.assertTrue(result["renameMovies"])

    def test_ensure_arr_common_settings_reconciles_all_sections(self) -> None:
        with mock.patch.object(haac, "ensure_arr_config_fragment") as ensure_fragment:
            haac.ensure_arr_common_settings(7878, app_name="Lidarr", api_key="lidarr-key", api_version="v1")

        self.assertEqual(ensure_fragment.call_count, 3)
        self.assertEqual(ensure_fragment.call_args_list[0].kwargs["config_name"], "naming")
        self.assertEqual(ensure_fragment.call_args_list[0].kwargs["desired"], haac.ARR_COMMON_NAMING_DEFAULTS["lidarr"])
        self.assertEqual(ensure_fragment.call_args_list[1].kwargs["config_name"], "mediamanagement")
        self.assertEqual(
            ensure_fragment.call_args_list[1].kwargs["desired"],
            haac.ARR_COMMON_MEDIA_MANAGEMENT_DEFAULTS,
        )
        self.assertEqual(ensure_fragment.call_args_list[2].kwargs["config_name"], "downloadclient")
        self.assertEqual(
            ensure_fragment.call_args_list[2].kwargs["desired"],
            haac.ARR_COMMON_DOWNLOAD_CLIENT_DEFAULTS,
        )

    def test_whisparr_naming_defaults_use_relative_movie_subpath(self) -> None:
        naming = haac.ARR_COMMON_NAMING_DEFAULTS["whisparr"]

        self.assertEqual(naming["movieFolderFormat"], "Movies/{Movie CleanTitle} ({Release Year})")
        self.assertTrue(naming["renameMovies"])

    def test_canonical_arr_language_preferences_defaults_to_italian_then_english(self) -> None:
        self.assertEqual(haac.canonical_arr_language_preferences(""), ("Italian", "English"))

    def test_canonical_arr_language_preferences_normalizes_codes_and_deduplicates(self) -> None:
        self.assertEqual(
            haac.canonical_arr_language_preferences("it, english, ita"),
            ("Italian", "English"),
        )

    def test_canonical_arr_language_preferences_rejects_unknown_values(self) -> None:
        with self.assertRaises(haac.HaaCError):
            haac.canonical_arr_language_preferences("it,jp")

    def test_build_arr_language_custom_format_uses_schema_template_and_language_value(self) -> None:
        payload = haac.build_arr_language_custom_format(
            {
                "implementation": "LanguageSpecification",
                "fields": [
                    {"name": "value", "value": 0, "selectOptions": [{"name": "Italian", "value": 5}]},
                    {"name": "exceptLanguage", "value": True},
                ],
            },
            format_name="HAAC Language: Prefer Italian",
            language_value=5,
        )

        self.assertEqual(payload["name"], "HAAC Language: Prefer Italian")
        self.assertFalse(payload["includeCustomFormatWhenRenaming"])
        specification = payload["specifications"][0]
        self.assertEqual(specification["name"], "HAAC Language: Prefer Italian matcher")
        fields = haac.json_array(specification["fields"])
        self.assertEqual(haac.field_value(fields, "value"), 5)
        self.assertFalse(haac.field_value(fields, "exceptLanguage"))

    def test_ensure_arr_language_custom_format_creates_language_spec(self) -> None:
        persisted = {
            "id": 91,
            "name": "HAAC Language: Prefer Italian",
            "specifications": [{"fields": [{"name": "value", "value": 5}, {"name": "exceptLanguage", "value": False}]}],
        }
        with mock.patch.object(
            haac,
            "http_request_json",
            side_effect=[
                [
                    {
                        "implementation": "LanguageSpecification",
                        "fields": [
                            {"name": "value", "value": 0, "selectOptions": [{"name": "Italian", "value": 5}]},
                            {"name": "exceptLanguage", "value": True},
                        ],
                    }
                ],
                [],
                {"id": 91},
                [persisted],
            ],
        ) as request_json:
            result = haac.ensure_arr_language_custom_format(
                8989,
                app_name="Sonarr",
                api_key="sonarr-key",
                format_name="HAAC Language: Prefer Italian",
                language_name="Italian",
            )

        payload = request_json.call_args_list[2].kwargs["payload"]
        self.assertEqual(payload["name"], "HAAC Language: Prefer Italian")
        self.assertEqual(result["id"], 91)

    def test_ensure_arr_language_preferences_updates_quality_profiles(self) -> None:
        initial_profiles = [
            {"id": 1, "name": "Any", "formatItems": []},
            {"id": 2, "name": "WEB-1080p", "formatItems": [{"format": 91, "name": "HAAC Language: Prefer Italian", "score": 10}]},
        ]
        refreshed_profiles = [
            {
                "id": 1,
                "name": "Any",
                "formatItems": [
                    {"format": 91, "name": "HAAC Language: Prefer Italian", "score": 200},
                    {"format": 92, "name": "HAAC Language: Prefer English", "score": 50},
                ],
            },
            {
                "id": 2,
                "name": "WEB-1080p",
                "formatItems": [
                    {"format": 91, "name": "HAAC Language: Prefer Italian", "score": 200},
                    {"format": 92, "name": "HAAC Language: Prefer English", "score": 50},
                ],
            },
        ]

        def fake_request_json(
            url: str,
            *,
            method: str = "GET",
            payload: dict[str, object] | None = None,
            headers: dict[str, str] | None = None,
            opener: object | None = None,
            timeout: int = 60,
        ) -> object:
            if url.endswith("/qualityprofile") and method == "GET":
                fake_request_json.calls += 1
                return initial_profiles if fake_request_json.calls == 1 else refreshed_profiles
            if "/qualityprofile/" in url and method == "PUT":
                return payload or {}
            raise AssertionError((url, method))

        fake_request_json.calls = 0

        with mock.patch.object(
            haac,
            "ensure_arr_language_custom_format",
            side_effect=[
                {"id": 91, "name": "HAAC Language: Prefer Italian"},
                {"id": 92, "name": "HAAC Language: Prefer English"},
            ],
        ):
            with mock.patch.object(haac, "http_request_json", side_effect=fake_request_json):
                haac.ensure_arr_language_preferences(
                    7878,
                    app_name="Radarr",
                    api_key="radarr-key",
                    preferred_languages=("Italian", "English"),
                )

    def test_jellyfin_default_libraries_match_movies_tv_and_music_paths(self) -> None:
        self.assertEqual(
            haac.JELLYFIN_DEFAULT_LIBRARIES,
            (
                {"name": "Movies", "collectionType": "movies", "path": "/data/movies"},
                {"name": "TV Shows", "collectionType": "tvshows", "path": "/data/tv"},
                {"name": "Music", "collectionType": "music", "path": "/data/music"},
                {"name": "Adult Movies", "collectionType": "movies", "path": "/data/adult"},
            ),
        )

    def test_ensure_jellyfin_admin_ready_bootstraps_first_run_then_authenticates(self) -> None:
        with mock.patch.object(
            haac,
            "http_request_json",
            side_effect=[
                {"StartupWizardCompleted": False},
                {"Name": "root"},
                {
                    "ServerName": "",
                    "UICulture": "en-US",
                    "MetadataCountryCode": "US",
                    "PreferredMetadataLanguage": "en",
                },
                {"StartupWizardCompleted": True},
                {"AccessToken": "token"},
            ],
        ):
            with mock.patch.object(haac, "http_request_text", side_effect=[(204, ""), (204, ""), (204, "")]) as request:
                info = haac.ensure_jellyfin_admin_ready(
                    8096,
                    username="jf-admin",
                    password="secret-pass",
                    domain_name="example.com",
                )

        self.assertTrue(info["StartupWizardCompleted"])
        config_payload = request.call_args_list[0].kwargs["payload"]
        user_payload = request.call_args_list[1].kwargs["payload"]
        self.assertEqual(config_payload["ServerName"], "jellyfin.example.com")
        self.assertEqual(config_payload["UICulture"], "it-IT")
        self.assertEqual(config_payload["MetadataCountryCode"], "IT")
        self.assertEqual(config_payload["PreferredMetadataLanguage"], "it")
        self.assertEqual(user_payload["Name"], "jf-admin")
        self.assertEqual(user_payload["Password"], "secret-pass")

    def test_ensure_jellyfin_system_configuration_reconciles_italian_defaults(self) -> None:
        with mock.patch.object(
            haac,
            "http_request_json",
            side_effect=[
                {
                    "UICulture": "en-US",
                    "MetadataCountryCode": "US",
                    "PreferredMetadataLanguage": "en",
                },
                {
                    "UICulture": "it-IT",
                    "MetadataCountryCode": "IT",
                    "PreferredMetadataLanguage": "it",
                },
            ],
        ):
            with mock.patch.object(haac, "http_request_text", return_value=(204, "")) as request:
                result = haac.ensure_jellyfin_system_configuration(8096, access_token="token")

        payload = request.call_args.kwargs["payload"]
        self.assertEqual(payload["UICulture"], "it-IT")
        self.assertEqual(payload["MetadataCountryCode"], "IT")
        self.assertEqual(payload["PreferredMetadataLanguage"], "it")
        self.assertEqual(result["UICulture"], "it-IT")

    def test_ensure_jellyfin_libraries_creates_missing_virtual_folders(self) -> None:
        with mock.patch.object(
            haac,
            "http_request_json",
            side_effect=[
                [],
                [{"Name": "Movies", "Locations": ["/data/movies"]}],
                [
                    {"Name": "Movies", "Locations": ["/data/movies"]},
                    {"Name": "TV Shows", "Locations": ["/data/tv"]},
                ],
                [
                    {"Name": "Movies", "Locations": ["/data/movies"]},
                    {"Name": "TV Shows", "Locations": ["/data/tv"]},
                    {"Name": "Music", "Locations": ["/data/music"]},
                ],
                [
                    {"Name": "Movies", "Locations": ["/data/movies"]},
                    {"Name": "TV Shows", "Locations": ["/data/tv"]},
                    {"Name": "Music", "Locations": ["/data/music"]},
                    {"Name": "Adult Movies", "Locations": ["/data/adult"]},
                ],
            ],
        ):
            with mock.patch.object(haac, "http_request_text", side_effect=[(204, ""), (204, ""), (204, ""), (204, "")]) as request:
                folders = haac.ensure_jellyfin_libraries(8096, access_token="demo-token")

        self.assertEqual(len(folders), 4)
        first_url = request.call_args_list[0].args[0]
        second_url = request.call_args_list[1].args[0]
        third_url = request.call_args_list[2].args[0]
        fourth_url = request.call_args_list[3].args[0]
        self.assertIn("collectionType=movies", first_url)
        self.assertIn("paths=%2Fdata%2Fmovies", first_url)
        self.assertIn("collectionType=tvshows", second_url)
        self.assertIn("paths=%2Fdata%2Ftv", second_url)
        self.assertIn("collectionType=music", third_url)
        self.assertIn("paths=%2Fdata%2Fmusic", third_url)
        self.assertIn("collectionType=movies", fourth_url)
        self.assertIn("paths=%2Fdata%2Fadult", fourth_url)

    def test_parser_registers_reconcile_media_stack(self) -> None:
        parser = haac.build_parser()
        args = parser.parse_args(
            [
                "reconcile-media-stack",
                "--master-ip",
                "192.168.0.211",
                "--proxmox-host",
                "pve",
                "--kubeconfig",
                "demo-kubeconfig",
            ]
        )

        self.assertIs(args.func, haac.cmd_reconcile_media_stack)

    def test_reconcile_media_stack_uses_downloader_credentials_from_env(self) -> None:
        @contextlib.contextmanager
        def fake_cluster_session(*_args, **_kwargs):
            yield Path("demo-kubeconfig")

        @contextlib.contextmanager
        def fake_port_forward(*_args, **_kwargs):
            yield 8080

        env = {
            "DOMAIN_NAME": "example.com",
            "QUI_PASSWORD": "qui-secret",
            "QBITTORRENT_USERNAME": "qbit-user",
        }

        with mock.patch.object(haac, "merged_env", return_value=env):
            with mock.patch.object(haac, "cluster_session", fake_cluster_session):
                with mock.patch.object(haac, "seerr_admin_identity", return_value=("jf-admin", "jf-pass", "jf@example.com")):
                    with mock.patch.object(
                        haac,
                        "read_arr_service_api_key",
                        side_effect=["radarr-key", "sonarr-key", "prowlarr-key", "lidarr-key"],
                    ):
                        with mock.patch.object(haac, "read_sabnzbd_service_api_key", return_value="sab-key"):
                            with mock.patch.object(haac, "wait_for_rollout"):
                                with mock.patch.object(haac, "bootstrap_downloaders_session"):
                                    with mock.patch.object(haac, "ensure_qbittorrent_app_preferences", return_value={}):
                                        with mock.patch.object(haac, "ensure_qbittorrent_category_paths", return_value={}):
                                            with mock.patch.object(haac, "kubectl_port_forward", fake_port_forward):
                                                with mock.patch.object(haac, "require_http_status"):
                                                    with mock.patch.object(haac, "ensure_media_storage_path"):
                                                        with mock.patch.object(haac, "ensure_sabnzbd_bootstrap"):
                                                            with mock.patch.object(haac, "ensure_arr_root_folder", return_value=[]):
                                                                with mock.patch.object(
                                                                    haac,
                                                                    "ensure_arr_qbittorrent_download_client",
                                                                    side_effect=RuntimeError("stop-after-radarr"),
                                                                ) as ensure_client:
                                                                    with self.assertRaisesRegex(RuntimeError, "stop-after-radarr"):
                                                                        haac.reconcile_media_stack(
                                                                            "192.168.0.211",
                                                                            "192.168.0.200",
                                                                            Path("demo-kubeconfig"),
                                                                            "kubectl",
                                                                        )

        self.assertEqual(ensure_client.call_args.kwargs["username"], "qbit-user")
        self.assertEqual(ensure_client.call_args.kwargs["password"], "qui-secret")

    def test_seerr_admin_identity_prefers_effective_jellyfin_overrides(self) -> None:
        username, password, email = haac.seerr_admin_identity(
            {
                "DOMAIN_NAME": "example.com",
                "HAAC_MAIN_USERNAME": "main-user",
                "HAAC_MAIN_PASSWORD": "main-pass",
                "JELLYFIN_ADMIN_USERNAME": "jf-admin",
                "JELLYFIN_ADMIN_PASSWORD": "jf-pass",
                "JELLYFIN_ADMIN_EMAIL": "jf@example.com",
            }
        )

        self.assertEqual(username, "jf-admin")
        self.assertEqual(password, "jf-pass")
        self.assertEqual(email, "jf@example.com")


class ArrStackRepoFileTests(unittest.TestCase):
    def test_taskfiles_wire_media_post_install(self) -> None:
        taskfile = (ROOT / "Taskfile.yml").read_text(encoding="utf-8")
        media_taskfile = (ROOT / "Taskfile.media.yml").read_text(encoding="utf-8")
        chaos_taskfile = (ROOT / "Taskfile.chaos.yml").read_text(encoding="utf-8")
        security_taskfile = (ROOT / "Taskfile.security.yml").read_text(encoding="utf-8")
        internal_taskfile = (ROOT / "Taskfile.internal.yml").read_text(encoding="utf-8")

        self.assertIn("media:\n    taskfile: ./Taskfile.media.yml", taskfile)
        self.assertIn("- task: media:post-install", taskfile)
        self.assertIn("reconcile-media-stack", media_taskfile)
        self.assertIn("verify:arr-flow", taskfile)
        self.assertIn("media:verify-flow", taskfile)
        self.assertIn("verify-arr-flow", media_taskfile)
        self.assertIn('"scripts/haac.py" master-ip', taskfile)
        self.assertIn('"scripts/haac.py" master-ip', media_taskfile)
        self.assertIn('"scripts/haac.py" master-ip', chaos_taskfile)
        self.assertIn('"scripts/haac.py" master-ip', security_taskfile)
        self.assertIn('"scripts/haac.py" master-ip', internal_taskfile)
        self.assertIn('verify-web --domain "{{.DOMAIN_NAME_VALUE}}" --master-ip "{{.MASTER_IP}}"', internal_taskfile)
        self.assertIn("clear-crowdsec-operator-ban", internal_taskfile)

    def test_env_example_documents_jellyfin_admin_overrides(self) -> None:
        env_example = (ROOT / ".env.example").read_text(encoding="utf-8")

        self.assertIn("JELLYFIN_ADMIN_USERNAME", env_example)
        self.assertIn("JELLYFIN_ADMIN_PASSWORD", env_example)
        self.assertIn("JELLYFIN_ADMIN_EMAIL", env_example)
        self.assertIn("BAZARR_AUTH_USERNAME", env_example)
        self.assertIn("BAZARR_AUTH_PASSWORD", env_example)
        self.assertIn("BAZARR_LANGUAGES", env_example)
        self.assertIn("ARR_PREFERRED_AUDIO_LANGUAGES", env_example)
        self.assertIn("appends the required `+pmp` suffix automatically", env_example)

    def test_readme_documents_media_post_install_surface(self) -> None:
        readme = (ROOT / "README.md").read_text(encoding="utf-8")

        self.assertIn("media:post-install", readme)
        self.assertIn("JELLYFIN_ADMIN_*", readme)
        self.assertIn("BAZARR_AUTH_*", readme)
        self.assertIn("BAZARR_LANGUAGES", readme)
        self.assertIn("ARR_PREFERRED_AUDIO_LANGUAGES", readme)
        self.assertIn("PROTONVPN_OPENVPN_USERNAME", readme)
        self.assertIn("ends in `+pmp`", readme)
        self.assertIn("radarr-imported", readme)
        self.assertIn("tv-sonarr-imported", readme)
        self.assertIn("lidarr-imported", readme)
        self.assertIn("whisparr-imported", readme)
        self.assertIn("Whisparr", readme)
        self.assertIn("SABnzbd", readme)
        self.assertIn("/data/usenet/complete", readme)
        self.assertIn("renameMovies", readme)
        self.assertIn("renameEpisodes", readme)
        self.assertIn("renameTracks", readme)
        self.assertIn("Italian-first media preference", readme)
        self.assertIn("request broker, not an indexer manager", readme)
        self.assertIn("Music library", readme)
        self.assertIn("Readarr` stays deferred", readme)
        self.assertIn("archived/deprecated", readme)
        self.assertIn("public application URL", readme)
        self.assertIn("docs/reference/operator-bootstrap.md", readme)
        self.assertIn("docs/reference/media-stack.md", readme)
        self.assertIn("docs/reference/security-stack.md", readme)

    def test_reference_docs_cover_bootstrap_media_and_security_contracts(self) -> None:
        operator = (ROOT / "docs" / "reference" / "operator-bootstrap.md").read_text(encoding="utf-8")
        media = (ROOT / "docs" / "reference" / "media-stack.md").read_text(encoding="utf-8")
        security = (ROOT / "docs" / "reference" / "security-stack.md").read_text(encoding="utf-8")
        task_up_runbook = (ROOT / "docs" / "runbooks" / "task-up.md").read_text(encoding="utf-8")

        self.assertIn("task up", operator)
        self.assertIn("`.env`", operator)
        self.assertIn("task down", operator)
        self.assertIn("Seerr is a request broker", media)
        self.assertIn("Prowlarr is the indexer source of truth", media)
        self.assertIn("Italian-First Defaults", media)
        self.assertIn("Cloudflare", security)
        self.assertIn("CrowdSec", security)
        self.assertIn("volumetric DDoS", security)
        self.assertIn("docs/reference/operator-bootstrap.md", task_up_runbook)


class EndpointVerificationTests(unittest.TestCase):
    def test_parse_cloudflare_trace_ip_extracts_valid_address(self) -> None:
        body = "fl=22f23\nh=www.cloudflare.com\nip=203.0.113.24\nts=1234"
        self.assertEqual(haac.parse_cloudflare_trace_ip(body), "203.0.113.24")

    def test_crowdsec_has_operator_probe_ban_detects_matching_ip(self) -> None:
        payload = [
            {
                "scenario": "crowdsecurity/crowdsec-appsec-outofband",
                "decisions": [{"scope": "Ip", "value": "203.0.113.24"}],
            },
            {
                "scenario": "LePresidente/http-generic-403-bf",
                "decisions": [{"scope": "Ip", "value": "203.0.113.24"}],
            }
        ]
        self.assertTrue(haac.crowdsec_has_operator_probe_ban(payload, "203.0.113.24"))
        self.assertFalse(haac.crowdsec_has_operator_probe_ban(payload, "203.0.113.25"))
        self.assertEqual(haac.crowdsec_operator_probe_ban_ips(payload), {"203.0.113.24"})
        self.assertEqual(
            haac.crowdsec_operator_probe_ban_scenarios(payload, "203.0.113.24"),
            {"crowdsecurity/crowdsec-appsec-outofband", "LePresidente/http-generic-403-bf"},
        )

    def test_crowdsec_http_probing_ban_only_matches_supported_false_positive_routes(self) -> None:
        payload = [
            {
                "scenario": "crowdsecurity/http-probing",
                "decisions": [{"scope": "Ip", "value": "203.0.113.24"}],
                "events": [
                    {
                        "meta": [
                            {"key": "http_path", "value": "/api/live/ws"},
                            {"key": "http_verb", "value": "GET"},
                        ]
                    },
                    {
                        "meta": [
                            {"key": "http_path", "value": "/apis/features.grafana.app/v0alpha1/namespaces/default/ofrep/v1/evaluate/flags"},
                            {"key": "http_verb", "value": "POST"},
                        ]
                    },
                ],
            }
        ]
        self.assertTrue(haac.crowdsec_has_operator_probe_ban(payload, "203.0.113.24"))
        self.assertEqual(haac.crowdsec_operator_probe_ban_scenarios(payload, "203.0.113.24"), {"crowdsecurity/http-probing"})

    def test_crowdsec_http_probing_ban_matches_servarr_signalr_negotiate(self) -> None:
        payload = [
            {
                "scenario": "crowdsecurity/http-probing",
                "decisions": [{"scope": "Ip", "value": "203.0.113.24"}],
                "events": [
                    {
                        "meta": [
                            {"key": "http_path", "value": "/signalr/messages/negotiate?access_token=abc123&negotiateVersion=1"},
                            {"key": "http_verb", "value": "POST"},
                        ]
                    }
                ],
            }
        ]
        self.assertTrue(haac.crowdsec_has_operator_probe_ban(payload, "203.0.113.24"))
        self.assertEqual(haac.crowdsec_operator_probe_ban_scenarios(payload, "203.0.113.24"), {"crowdsecurity/http-probing"})

    def test_crowdsec_http_probing_ban_ignores_non_allowlisted_routes(self) -> None:
        payload = [
            {
                "scenario": "crowdsecurity/http-probing",
                "decisions": [{"scope": "Ip", "value": "203.0.113.24"}],
                "events": [
                    {
                        "meta": [
                            {"key": "http_path", "value": "/admin"},
                            {"key": "http_verb", "value": "GET"},
                        ]
                    }
                ],
            }
        ]
        self.assertFalse(haac.crowdsec_has_operator_probe_ban(payload, "203.0.113.24"))
        self.assertEqual(haac.crowdsec_operator_probe_ban_scenarios(payload, "203.0.113.24"), set())

    def test_crowdsec_appsec_ban_matches_target_uri_without_http_verb(self) -> None:
        payload = [
            {
                "scenario": "crowdsecurity/crowdsec-appsec-outofband",
                "decisions": [{"id": 12, "scope": "Ip", "value": "203.0.113.24"}],
                "events": [
                    {
                        "meta": [
                            {"key": "target_uri", "value": "/homelab"},
                        ]
                    },
                    {
                        "meta": [
                            {"key": "target_uri", "value": "[\"/Sessions/Playing/Progress\"]"},
                        ]
                    },
                ],
            }
        ]
        self.assertTrue(haac.crowdsec_has_operator_probe_ban(payload, "203.0.113.24"))
        self.assertEqual(
            haac.crowdsec_operator_probe_ban_scenarios(payload, "203.0.113.24"),
            {"crowdsecurity/crowdsec-appsec-outofband"},
        )
        self.assertEqual(haac.crowdsec_operator_probe_ban_decision_ids(payload, "203.0.113.24"), {"12"})

    def test_crowdsec_appsec_ban_matches_grafana_prometheus_proxy_query(self) -> None:
        payload = [
            {
                "scenario": "crowdsecurity/crowdsec-appsec-outofband",
                "decisions": [{"id": 24, "scope": "Ip", "value": "203.0.113.24"}],
                "events": [
                    {
                        "meta": [
                            {
                                "key": "target_uri",
                                "value": '/api/datasources/proxy/uid/prometheus/api/v1/query?query=count(up%7Bnamespace%3D%22kyverno%22%7D)',
                            }
                        ]
                    }
                ],
            }
        ]
        self.assertTrue(haac.crowdsec_has_operator_probe_ban(payload, "203.0.113.24"))
        self.assertEqual(
            haac.crowdsec_operator_probe_ban_decision_ids(payload, "203.0.113.24"),
            {"24"},
        )

    def test_verify_web_retries_once_after_crowdsec_operator_ban_cleanup(self) -> None:
        endpoint = {
            "name": "auth",
            "namespace": "mgmt",
            "url": "https://auth.example.com",
            "auth": "public",
        }
        responses = iter(
            [
                {"status": 403, "location": "", "body": ""},
                {"status": 200, "location": "", "body": "<html>ok</html>"},
            ]
        )
        with mock.patch.object(haac, "load_endpoint_specs", return_value=[endpoint]):
            with mock.patch.object(haac.endpointlib, "probe_web_response", side_effect=lambda url: next(responses)):
                with mock.patch.object(
                    haac.endpointlib,
                    "endpoint_verification_success",
                    side_effect=lambda endpoint, response, auth_url: int(response["status"]) == 200,
                ):
                    with mock.patch.object(haac, "clear_current_operator_crowdsec_probe_ban", return_value=True) as clear_mock:
                        with mock.patch.object(haac, "restart_traefik_for_crowdsec_recovery", return_value=True) as restart_mock:
                            with contextlib.redirect_stdout(io.StringIO()):
                                haac.verify_web(
                                    "example.com",
                                    retries=1,
                                    sleep_seconds=0,
                                    master_ip="192.168.0.10",
                                    proxmox_host="192.168.0.20",
                                    kubeconfig=Path("demo"),
                                    kubectl="kubectl",
                                )
        clear_mock.assert_called_once_with("192.168.0.10", "192.168.0.20", Path("demo"), "kubectl")
        restart_mock.assert_called_once_with("192.168.0.10", "192.168.0.20", Path("demo"), "kubectl")

    def test_recyclarr_config_template_vendors_official_profiles_with_secret_refs(self) -> None:
        config = (
            ROOT
            / "k8s"
            / "charts"
            / "haac-stack"
            / "charts"
            / "media"
            / "files"
            / "recyclarr"
            / "recyclarr.yml"
        ).read_text(encoding="utf-8")

        self.assertIn("base_url: !secret radarr_main_base_url", config)
        self.assertIn("api_key: !secret radarr_main_api_key", config)
        self.assertIn("base_url: !secret sonarr_main_base_url", config)
        self.assertIn("api_key: !secret sonarr_main_api_key", config)
        self.assertIn("type: movie", config)
        self.assertIn("type: series", config)
        self.assertIn("name: HD Bluray + WEB", config)
        self.assertIn("name: WEB-1080p", config)

    def test_verify_public_auth_covers_seerr_and_arr_dashboard(self) -> None:
        verifier = (ROOT / "scripts" / "verify-public-auth.mjs").read_text(encoding="utf-8")
        haac_script = (ROOT / "scripts" / "haac.py").read_text(encoding="utf-8")

        self.assertIn('const GRAFANA_ARR_STACK_DASHBOARD_UID = "haac-arr-stack-overview";', verifier)
        self.assertIn('async function visibleBodyText(page)', verifier)
        self.assertIn('const body = await visibleBodyText(page);', verifier)
        self.assertNotIn("/api/datasources/proxy/uid/", verifier)
        self.assertNotIn("assertGrafanaMetricPresent", verifier)
        self.assertNotIn("queryGrafanaPrometheus", verifier)
        self.assertIn('bazarr: { appNativeSelector:', verifier)
        self.assertIn('lidarr: { appNativeSelector:', verifier)
        self.assertIn('whisparr: { appNativeSelector:', verifier)
        self.assertIn('sabnzbd:', verifier)
        self.assertIn("seerr: {", verifier)
        self.assertIn('bodyText.includes("Seerr")', verifier)
        self.assertIn('bodyText.includes("Lidarr")', verifier)
        self.assertIn('bodyText.includes("SABnzbd")', verifier)
        self.assertIn('currentUrl.pathname.startsWith("/setup")', verifier)
        self.assertIn("buildVerifierSafeRouteMatcher", verifier)
        self.assertIn('allowNoData: true', verifier)
        self.assertIn('pathPrefixes: ["/signalr/messages/negotiate"]', verifier)
        self.assertIn('`${name}.${domainName}`', verifier)
        self.assertIn('pathPrefixes: ["/homelab", "/haac-alerts"]', verifier)
        self.assertIn('assertGrafanaDashboardHealthy(apiServerBodyText, "Kubernetes API server dashboard", []);', verifier)
        self.assertIn('assertGrafanaDashboardHealthy(argoBodyText, "ArgoCD dashboard", [], { allowNoData: true });', verifier)
        self.assertIn("wait_for_argocd_child_applications_ready", haac_script)
        self.assertIn('ServiceMonitor" in version "monitoring.coreos.com/v1', haac_script)
        self.assertIn("recover_stale_crowdsec_runtime_registrations", haac_script)

    def test_arr_dashboard_configmap_is_repo_managed(self) -> None:
        dashboard = (ROOT / "k8s" / "platform" / "observability" / "arr-stack-dashboard-configmap.yaml").read_text(
            encoding="utf-8"
        )

        self.assertIn("arr-stack-overview.json", dashboard)
        self.assertIn('"uid": "haac-arr-stack-overview"', dashboard)
        self.assertIn("radarr_movie_total", dashboard)
        self.assertIn("lidarr_artists_total", dashboard)
        self.assertIn("sabnzbd_queue_length", dashboard)
        self.assertIn("autobrr_info", dashboard)
        self.assertIn("bazarr_system_status", dashboard)
        self.assertIn("unpackerr_uptime_seconds_total", dashboard)

    def test_media_manifests_expose_supported_metrics(self) -> None:
        downloaders = (
            ROOT / "k8s" / "charts" / "haac-stack" / "charts" / "downloaders" / "templates" / "downloaders.yaml"
        ).read_text(encoding="utf-8")
        autobrr = (
            ROOT / "k8s" / "charts" / "haac-stack" / "charts" / "media" / "templates" / "autobrr.yaml"
        ).read_text(encoding="utf-8")
        flaresolverr = (
            ROOT / "k8s" / "charts" / "haac-stack" / "charts" / "media" / "templates" / "helpers.yaml"
        ).read_text(encoding="utf-8")
        radarr = (
            ROOT / "k8s" / "charts" / "haac-stack" / "charts" / "media" / "templates" / "radarr.yaml"
        ).read_text(encoding="utf-8")
        sonarr = (
            ROOT / "k8s" / "charts" / "haac-stack" / "charts" / "media" / "templates" / "sonarr.yaml"
        ).read_text(encoding="utf-8")
        prowlarr = (
            ROOT / "k8s" / "charts" / "haac-stack" / "charts" / "media" / "templates" / "prowlarr.yaml"
        ).read_text(encoding="utf-8")
        lidarr = (
            ROOT / "k8s" / "charts" / "haac-stack" / "charts" / "media" / "templates" / "lidarr.yaml"
        ).read_text(encoding="utf-8")
        whisparr = (
            ROOT / "k8s" / "charts" / "haac-stack" / "charts" / "media" / "templates" / "whisparr.yaml"
        ).read_text(encoding="utf-8")
        sabnzbd = (
            ROOT / "k8s" / "charts" / "haac-stack" / "charts" / "media" / "templates" / "sabnzbd.yaml"
        ).read_text(encoding="utf-8")
        seerr = (
            ROOT / "k8s" / "charts" / "haac-stack" / "charts" / "media" / "templates" / "seerr.yaml"
        ).read_text(encoding="utf-8")
        bazarr = (
            ROOT / "k8s" / "charts" / "haac-stack" / "charts" / "media" / "templates" / "bazarr.yaml"
        ).read_text(encoding="utf-8")
        unpackerr = (
            ROOT / "k8s" / "charts" / "haac-stack" / "charts" / "media" / "templates" / "unpackerr.yaml"
        ).read_text(encoding="utf-8")
        prometheus_app = (
            ROOT / "k8s" / "platform" / "applications" / "kube-prometheus-stack-app.yaml.template"
        ).read_text(encoding="utf-8")

        self.assertIn("AUTOBRR__METRICS_ENABLED", autobrr)
        self.assertIn("port: 9074", autobrr)
        self.assertIn("labels:\n    app: autobrr", autobrr)
        self.assertIn("PROMETHEUS_ENABLED", flaresolverr)
        self.assertIn("labels:\n    app: flaresolverr", flaresolverr)
        self.assertIn("labels:\n    app: radarr", radarr)
        self.assertIn("labels:\n    app: sonarr", sonarr)
        self.assertIn("labels:\n    app: prowlarr", prowlarr)
        self.assertIn("labels:\n    app: lidarr", lidarr)
        self.assertIn('args: ["lidarr"]', lidarr)
        self.assertIn("LIDARR_API_KEY", lidarr)
        self.assertIn("labels:\n    app: whisparr", whisparr)
        self.assertIn("containerPort: 6969", whisparr)
        self.assertIn("labels:\n    app: sabnzbd", sabnzbd)
        self.assertIn('args: ["sabnzbd"]', sabnzbd)
        self.assertIn("SABNZBD_API_KEY", sabnzbd)
        self.assertIn("labels:\n    app: downloaders", downloaders)
        self.assertIn("/data/torrents/radarr", downloaders)
        self.assertIn("/data/torrents/tv-sonarr", downloaders)
        self.assertIn("/data/media/music", downloaders)
        self.assertIn("/data/media/adult", downloaders)
        self.assertIn("/data/torrents/lidarr", downloaders)
        self.assertIn("/data/torrents/whisparr", downloaders)
        self.assertIn("/data/torrents/prowlarr", downloaders)
        self.assertIn("/data/torrents/radarr-imported", downloaders)
        self.assertIn("/data/torrents/tv-sonarr-imported", downloaders)
        self.assertIn("/data/torrents/lidarr-imported", downloaders)
        self.assertIn("/data/torrents/whisparr-imported", downloaders)
        self.assertIn("name: bazarr-exportarr", bazarr)
        self.assertIn('args: ["bazarr"]', bazarr)
        self.assertIn("API_KEY", bazarr)
        self.assertIn("labels:\n        app: bazarr-exportarr", bazarr)
        self.assertIn("name: bazarr-metrics", bazarr)
        self.assertIn('listen_addr = "0.0.0.0:5656"', unpackerr)
        self.assertIn("RADARR_API_KEY", unpackerr)
        self.assertIn("SONARR_API_KEY", unpackerr)
        self.assertIn("WHISPARR_API_KEY", unpackerr)
        self.assertIn("def normalize_api_key", unpackerr)
        self.assertIn("if len(value) != 32:", unpackerr)
        self.assertIn("[[whisparr]]", unpackerr)
        self.assertIn("labels:\n    app: unpackerr", unpackerr)
        self.assertIn("kind: StatefulSet", seerr)
        self.assertIn("/api/v1/settings/public", seerr)
        self.assertIn("- name: flaresolverr", prometheus_app)
        self.assertIn("- name: radarr", prometheus_app)
        self.assertIn("- name: sonarr", prometheus_app)
        self.assertIn("- name: prowlarr", prometheus_app)
        self.assertIn("- name: lidarr", prometheus_app)
        self.assertIn("- name: sabnzbd", prometheus_app)
        self.assertIn("- name: autobrr", prometheus_app)
        self.assertIn("- name: bazarr", prometheus_app)
        self.assertIn("- name: unpackerr", prometheus_app)
        self.assertIn("namespaceSelector:\n                matchNames:\n                  - media", prometheus_app)
        self.assertIn("argocd.argoproj.io/hook: PreSync", prometheus_app)

    def test_recyclarr_cronjob_mounts_repo_config_and_runtime_secret(self) -> None:
        helpers = (
            ROOT / "k8s" / "charts" / "haac-stack" / "charts" / "media" / "templates" / "helpers.yaml"
        ).read_text(encoding="utf-8")
        runtime_secret = (
            ROOT / "k8s" / "charts" / "haac-stack" / "charts" / "media" / "templates" / "recyclarr-runtime-secret.yaml"
        ).read_text(encoding="utf-8")
        haac_stack_template = (
            ROOT / "k8s" / "workloads" / "applications" / "haac-stack.yaml.template"
        ).read_text(encoding="utf-8")

        self.assertIn("name: recyclarr", helpers)
        self.assertIn("configMap:\n                name: recyclarr-config", helpers)
        self.assertIn("secret:\n                secretName: recyclarr-secrets", helpers)
        self.assertNotIn("persistentVolumeClaim:\n                claimName: recyclarr-config", helpers)
        self.assertIn("RADARR_API_KEY: bootstrapplaceholder1234", runtime_secret)
        self.assertIn("SONARR_API_KEY: bootstrapplaceholder1234", runtime_secret)
        self.assertIn("LIDARR_API_KEY: bootstrapplaceholder1234", runtime_secret)
        self.assertIn("BAZARR_API_KEY: bootstrapplaceholder1234", runtime_secret)
        self.assertIn("SABNZBD_API_KEY: bootstrapplaceholder1234", runtime_secret)
        self.assertIn("name: recyclarr-secrets", haac_stack_template)
        self.assertIn("jsonPointers:\n        - /data", haac_stack_template)

    def test_haac_stack_app_ignores_seerr_pvc_template_status(self) -> None:
        haac_stack_app = (ROOT / "k8s" / "workloads" / "applications" / "haac-stack.yaml").read_text(encoding="utf-8")

        self.assertIn("ignoreDifferences:", haac_stack_app)
        self.assertIn("name: seerr", haac_stack_app)
        self.assertIn(".spec.volumeClaimTemplates[]?.status", haac_stack_app)

    def test_crowdsec_platform_surface_is_repo_managed(self) -> None:
        app_template = (
            ROOT / "k8s" / "platform" / "applications" / "crowdsec-app.yaml.template"
        ).read_text(encoding="utf-8")
        traefik_template = (
            ROOT / "k8s" / "platform" / "traefik" / "traefik-config.yaml.template"
        ).read_text(encoding="utf-8")
        platform_kustomization = (ROOT / "k8s" / "platform" / "kustomization.yaml").read_text(encoding="utf-8")
        applications_kustomization = (
            ROOT / "k8s" / "platform" / "applications" / "kustomization.yaml"
        ).read_text(encoding="utf-8")
        namespaces = (ROOT / "k8s" / "bootstrap" / "root" / "namespaces.yaml").read_text(encoding="utf-8")

        self.assertIn("name: crowdsec", app_template)
        self.assertIn("chart: crowdsec", app_template)
        self.assertIn("BOUNCER_KEY_traefik", app_template)
        self.assertIn("unregister_on_exit: true", app_template)
        self.assertIn("auto_registration:", app_template)
        self.assertIn('token: "${REGISTRATION_TOKEN}"', app_template)
        self.assertIn('- "10.42.0.0/16"', app_template)
        self.assertIn("use_wal: true", app_template)
        self.assertIn("bouncers_autodelete:", app_template)
        self.assertIn("agents_autodelete:", app_template)
        self.assertIn("login_password: 1h", app_template)
        self.assertIn("crowdsecurity/traefik", app_template)
        self.assertIn("crowdsecurity/appsec-virtual-patching", app_template)
        self.assertIn("crowdsecurity/appsec-crs", app_template)
        self.assertIn("crowdsecurity/crs", app_template)
        self.assertIn("crowdsecurity/appsec-generic-rules", app_template)
        self.assertIn("crowdsecurity/http-crawl-non_statics", app_template)
        self.assertIn('name: "haac/operator-false-positives"', app_template)
        self.assertIn("evt.Meta.http_path == '/Sessions/Playing/Progress'", app_template)
        self.assertIn("evt.Meta.http_path == '/homelab'", app_template)
        self.assertIn("evt.Meta.http_path == '/haac-alerts'", app_template)
        self.assertIn("evt.Meta.http_path == '/api/live/ws'", app_template)
        self.assertIn("evt.Meta.http_path startsWith '/apis/features.grafana.app/'", app_template)
        self.assertIn("evt.Meta.http_path startsWith '/avatar/'", app_template)
        self.assertIn("name: custom/haac-operator-surface", app_template)
        self.assertIn('req.Host == "ntfy.${DOMAIN_NAME}"', app_template)
        self.assertIn('req.Host == "jellyfin.${DOMAIN_NAME}"', app_template)
        self.assertIn('req.Host == "grafana.${DOMAIN_NAME}"', app_template)
        self.assertIn('CancelEvent()', app_template)
        self.assertIn('SetRemediation("allow")', app_template)
        self.assertIn('CancelAlert()', app_template)
        self.assertIn("- custom/haac-operator-surface", app_template)
        self.assertIn("serviceMonitor:", app_template)
        self.assertIn("podMonitor:", app_template)
        self.assertIn("crowdsec-bouncer-traefik-plugin", traefik_template)
        self.assertIn("checksum/crowdsec-bouncer-secret", traefik_template)
        self.assertIn("--providers.file.directory=/etc/traefik/crowdsec/dynamic", traefik_template)
        self.assertIn("--entryPoints.web.http.middlewares=crowdsec-bouncer@file", traefik_template)
        self.assertIn("secretName: traefik-crowdsec-bouncer", traefik_template)
        self.assertIn("name: crowdsec", namespaces)
        self.assertIn("- crowdsec-app.yaml", applications_kustomization)
        self.assertIn("crowdsec/crowdsec-lapi-sealed-secret.yaml", platform_kustomization)
        self.assertIn("traefik/crowdsec-bouncer-sealed-secret.yaml", platform_kustomization)

    def test_crowdsec_dynamic_config_uses_stream_mode_and_appsec(self) -> None:
        rendered = haac.crowdsec_traefik_dynamic_config(
            {"TRAEFIK_TRUSTED_IPS": "10.42.0.0/16,103.21.244.0/22"}
        )

        self.assertIn("crowdsecMode: stream", rendered)
        self.assertIn("crowdsecLapiKeyFile: /etc/traefik/crowdsec/auth/crowdsec-lapi-key", rendered)
        self.assertIn("crowdsecAppsecEnabled: true", rendered)
        self.assertIn("crowdsecAppsecHost: crowdsec-appsec-service.crowdsec.svc.cluster.local:7422", rendered)
        self.assertIn("crowdsecAppsecUnreachableBlock: false", rendered)
        self.assertIn("forwardedHeadersTrustedIPs:", rendered)
        self.assertIn("- 10.42.0.0/16", rendered)
        self.assertIn("- 103.21.244.0/22", rendered)


class CrowdSecRuntimeRecoveryTests(unittest.TestCase):
    def test_parse_rfc3339_timestamp_returns_none_for_invalid_values(self) -> None:
        self.assertIsNone(haac.parse_rfc3339_timestamp(""))
        self.assertIsNone(haac.parse_rfc3339_timestamp("not-a-timestamp"))

    def test_stale_crowdsec_runtime_machine_names_only_returns_non_ready_stale_matches(self) -> None:
        machines = [
            {"machineId": "crowdsec-agent-a", "last_heartbeat": "2026-04-20T09:00:00Z"},
            {"machineId": "crowdsec-agent-b", "last_heartbeat": "2026-04-20T09:50:00Z"},
            {"machineId": "crowdsec-agent-c", "last_heartbeat": "2026-04-20T09:00:00Z"},
        ]
        pod_readiness = {
            "crowdsec-agent-a": False,
            "crowdsec-agent-b": False,
            "crowdsec-agent-c": True,
        }

        stale = haac.stale_crowdsec_runtime_machine_names(
            machines,
            pod_readiness,
            now=haac.parse_rfc3339_timestamp("2026-04-20T10:10:00Z"),
            stale_after_seconds=1800,
        )

        self.assertEqual(stale, ["crowdsec-agent-a"])

    def test_recover_stale_crowdsec_runtime_registrations_deletes_machine_and_pod(self) -> None:
        with mock.patch.object(haac, "crowdsec_lapi_pod_name", return_value="crowdsec-lapi-0"):
            with mock.patch.object(haac, "crowdsec_runtime_pod_readiness", return_value={"crowdsec-agent-a": False}):
                with mock.patch.object(haac, "crowdsec_registered_machines", return_value=[{"machineId": "crowdsec-agent-a"}]):
                    with mock.patch.object(haac, "stale_crowdsec_runtime_machine_names", return_value=["crowdsec-agent-a"]):
                        with mock.patch.object(haac, "delete_crowdsec_machine_registration") as delete_machine:
                            with mock.patch.object(haac, "delete_crowdsec_runtime_pod") as delete_pod:
                                with contextlib.redirect_stdout(io.StringIO()):
                                    result = haac.recover_stale_crowdsec_runtime_registrations("kubectl", Path("demo"))

        self.assertTrue(result)
        delete_machine.assert_called_once_with("kubectl", Path("demo"), lapi_pod="crowdsec-lapi-0", machine_name="crowdsec-agent-a")
        delete_pod.assert_called_once_with("kubectl", Path("demo"), pod_name="crowdsec-agent-a")


if __name__ == "__main__":
    unittest.main()
