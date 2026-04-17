from __future__ import annotations

import importlib.util
import io
import json
import os
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
        with mock.patch.object(haac, "load_env_file", return_value={"QUI_PASSWORD": "demo-secret"}):
            with mock.patch.dict(os.environ, {}, clear=True):
                merged = haac.merged_env()

        self.assertTrue(merged["QBITTORRENT_PASSWORD_PBKDF2"].startswith("@ByteArray("))
        self.assertEqual(
            merged["QBITTORRENT_PASSWORD_PBKDF2"],
            haac.qbittorrent_password_pbkdf2("demo-secret"),
        )
        self.assertIn("DOWNLOADERS_AUTH_SECRET_SHA256", merged)
        self.assertIn("HOMEPAGE_WIDGETS_SECRET_SHA256", merged)


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


class KnownHostsRefreshTests(unittest.TestCase):
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
        self.assertIn(str(haac.VALUES_OUTPUT), stage_paths)


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


if __name__ == "__main__":
    unittest.main()
