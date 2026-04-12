from __future__ import annotations

import io
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from datetime import datetime
from pathlib import Path
from unittest.mock import patch


SCRIPTS_DIR = Path(__file__).resolve().parents[1] / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

import haac_loop  # noqa: E402


ACTIVE_CHANGE = {
    "name": "align-loop-effective-mode",
    "completedTasks": 0,
    "totalTasks": 6,
    "lastModified": "2026-04-12T13:20:59.722Z",
    "status": "in-progress",
}


class HaaCLoopCliTests(unittest.TestCase):
    def run_cli(self, *args: str) -> tuple[int, str, str]:
        stdout = io.StringIO()
        stderr = io.StringIO()
        with patch.object(sys, "argv", ["haac_loop.py", *args]):
            with redirect_stdout(stdout), redirect_stderr(stderr):
                exit_code = haac_loop.main()
        return exit_code, stdout.getvalue(), stderr.getvalue()

    def test_apply_without_active_changes_reuses_same_day_worklog_across_cli_surfaces(self) -> None:
        with tempfile.TemporaryDirectory(dir=haac_loop.ROOT) as temp_dir:
            worklogs_dir = Path(temp_dir)
            day_dir = worklogs_dir / "2026-04-12"
            day_dir.mkdir(parents=True, exist_ok=True)
            reused_worklog = day_dir / "1510-fallback-check.md"
            reused_worklog.write_text(
                "# 2026-04-12 15:10 - fallback-check\n\n"
                "- mode: apply\n"
                "- active_changes: stale-change\n"
                "- notes:\n"
                "\n"
                "## Existing notes\n",
                encoding="utf-8",
            )

            fake_now = datetime(2026, 4, 12, 16, 15)
            relative_worklog = haac_loop.relpath(reused_worklog)
            with (
                patch.object(haac_loop, "WORKLOGS_DIR", worklogs_dir),
                patch.object(haac_loop, "active_changes", return_value=[]),
                patch.object(haac_loop, "check_loop"),
                patch.object(haac_loop, "seal_stale_tracker"),
                patch.object(haac_loop, "codex_potter_command", return_value=["codex-potter", "exec"]),
                patch.object(haac_loop, "datetime") as mock_datetime,
            ):
                mock_datetime.now.return_value = fake_now

                exit_code, prompt_stdout, prompt_stderr = self.run_cli(
                    "prompt",
                    "--slug",
                    "fallback-check",
                    "--mode",
                    "apply",
                )
                self.assertEqual(exit_code, 0, prompt_stderr)
                self.assertIn("- primary change: `none`", prompt_stdout)
                self.assertIn("- mode: `discover`", prompt_stdout)
                self.assertIn(f"- worklog: `{relative_worklog}`", prompt_stdout)

                exit_code, worklog_stdout, worklog_stderr = self.run_cli(
                    "worklog",
                    "--slug",
                    "fallback-check",
                    "--mode",
                    "apply",
                )
                self.assertEqual(exit_code, 0, worklog_stderr)
                worklog_path = haac_loop.ROOT / worklog_stdout.strip()
                self.assertEqual(worklog_path, reused_worklog)
                updated_worklog = worklog_path.read_text(encoding="utf-8")
                self.assertIn("- mode: discover", updated_worklog)
                self.assertIn("- active_changes: none", updated_worklog)
                self.assertIn("## Existing notes", updated_worklog)

                exit_code, run_stdout, run_stderr = self.run_cli(
                    "run",
                    "--slug",
                    "fallback-check",
                    "--rounds",
                    "1",
                    "--mode",
                    "apply",
                    "--dry-run",
                )
                self.assertEqual(exit_code, 0, run_stderr)
                self.assertIn("Dry run only.", run_stdout)
                self.assertIn("- mode: `discover`", run_stdout)
                self.assertIn(f"- worklog: `{relative_worklog}`", run_stdout)

    def test_cli_preserves_explicit_discover_and_apply_with_active_changes(self) -> None:
        with tempfile.TemporaryDirectory(dir=haac_loop.ROOT) as temp_dir:
            worklogs_dir = Path(temp_dir)
            fake_now = datetime(2026, 4, 12, 15, 11)
            with (
                patch.object(haac_loop, "WORKLOGS_DIR", worklogs_dir),
                patch.object(haac_loop, "active_changes", return_value=[ACTIVE_CHANGE]),
                patch.object(haac_loop, "check_loop"),
                patch.object(haac_loop, "seal_stale_tracker"),
                patch.object(haac_loop, "codex_potter_command", return_value=["codex-potter", "exec"]),
                patch.object(haac_loop, "datetime") as mock_datetime,
            ):
                mock_datetime.now.return_value = fake_now

                exit_code, discover_prompt, discover_stderr = self.run_cli(
                    "prompt",
                    "--slug",
                    "session",
                    "--mode",
                    "discover",
                )
                self.assertEqual(exit_code, 0, discover_stderr)
                self.assertIn("- primary change: `align-loop-effective-mode`", discover_prompt)
                self.assertIn("- mode: `discover`", discover_prompt)

                exit_code, apply_prompt, apply_stderr = self.run_cli(
                    "prompt",
                    "--slug",
                    "session",
                    "--mode",
                    "apply",
                )
                self.assertEqual(exit_code, 0, apply_stderr)
                self.assertIn("- primary change: `align-loop-effective-mode`", apply_prompt)
                self.assertIn("- mode: `apply`", apply_prompt)

                exit_code, worklog_stdout, worklog_stderr = self.run_cli(
                    "worklog",
                    "--slug",
                    "session",
                    "--mode",
                    "apply",
                )
                self.assertEqual(exit_code, 0, worklog_stderr)
                worklog_path = haac_loop.ROOT / worklog_stdout.strip()
                worklog_content = worklog_path.read_text(encoding="utf-8")
                self.assertEqual(worklog_path.name, "1511-session.md")
                self.assertIn("- mode: apply", worklog_content)
                self.assertIn("- active_changes: align-loop-effective-mode", worklog_content)

    def test_worklog_creates_new_minute_stamped_file_when_slug_has_no_same_day_match(self) -> None:
        with tempfile.TemporaryDirectory(dir=haac_loop.ROOT) as temp_dir:
            worklogs_dir = Path(temp_dir)
            day_dir = worklogs_dir / "2026-04-12"
            day_dir.mkdir(parents=True, exist_ok=True)
            existing_worklog = day_dir / "1510-other-session.md"
            existing_worklog.write_text(
                "# 2026-04-12 15:10 - other-session\n\n"
                "- mode: discover\n"
                "- active_changes: none\n"
                "- notes:\n",
                encoding="utf-8",
            )

            fake_now = datetime(2026, 4, 12, 17, 5)
            with (
                patch.object(haac_loop, "WORKLOGS_DIR", worklogs_dir),
                patch.object(haac_loop, "active_changes", return_value=[]),
                patch.object(haac_loop, "datetime") as mock_datetime,
            ):
                mock_datetime.now.return_value = fake_now

                worklog_path = haac_loop.ensure_worklog("session", "discover", [])

            self.assertEqual(worklog_path.name, "1705-session.md")
            self.assertEqual(worklog_path.parent.name, "2026-04-12")
            self.assertNotEqual(worklog_path, existing_worklog)
            self.assertTrue(worklog_path.exists())
            self.assertIn("- mode: discover", worklog_path.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
