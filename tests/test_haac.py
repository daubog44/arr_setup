from __future__ import annotations

import importlib.util
import os
import unittest
from pathlib import Path
from unittest import mock
import io


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


if __name__ == "__main__":
    unittest.main()
