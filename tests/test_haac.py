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
        self.assertIn(str(haac.LITMUS_MONGODB_SECRET_OUTPUT), stage_paths)
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
            if command[:3] == ["get", "secret", "litmus-mongodb"]:
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
