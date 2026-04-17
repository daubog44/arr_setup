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
