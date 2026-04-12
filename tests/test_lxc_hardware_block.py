from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = ROOT / "scripts" / "reconcile_lxc_hardware_block.py"
SCRIPT_SPEC = importlib.util.spec_from_file_location("reconcile_lxc_hardware_block", SCRIPT_PATH)
reconcile = importlib.util.module_from_spec(SCRIPT_SPEC)
assert SCRIPT_SPEC.loader is not None
SCRIPT_SPEC.loader.exec_module(reconcile)


class ReconcileLxcHardwareBlockTests(unittest.TestCase):
    def test_reconcile_moves_legacy_lines_into_managed_block(self) -> None:
        original = (
            "#K3s Master Node (Control Plane + Traefik) (HaaC v3)\n"
            "arch: amd64\n"
            "unprivileged: 1\n"
            "lxc.idmap: u 0 100000 13000\n"
            "lxc.mount.entry: /dev/net/tun dev/net/tun none bind,create=file\n"
            "lxc.mount.entry: /mnt/pve/zima data none bind,create=dir\n"
        )

        reconciled = reconcile.reconcile_lxc_config_text(
            original,
            [
                "lxc.idmap: u 0 100000 13000",
                "lxc.mount.entry: /dev/net/tun dev/net/tun none bind,create=file",
                "lxc.mount.entry: /mnt/pve/zima data none bind,create=dir",
            ],
        )

        self.assertEqual(
            reconciled,
            (
                "#K3s Master Node (Control Plane + Traefik) (HaaC v3)\n"
                "arch: amd64\n"
                "unprivileged: 1\n"
                "lxc.idmap: u 0 100000 13000\n"
                "lxc.mount.entry: /dev/net/tun dev/net/tun none bind,create=file\n"
                "lxc.mount.entry: /mnt/pve/zima data none bind,create=dir\n"
            ),
        )

    def test_reconcile_replaces_empty_marker_pair_with_canonical_managed_lines(self) -> None:
        original = (
            "#K3s Master Node (Control Plane + Traefik) (HaaC v3)\n"
            "# BEGIN HAAC MANAGED LXC HARDWARE\n"
            "# END HAAC MANAGED LXC HARDWARE\n"
            "arch: amd64\n"
            "unprivileged: 1\n"
            "lxc.idmap: u 0 100000 13000\n"
            "lxc.mount.entry: /dev/net/tun dev/net/tun none bind,create=file\n"
            "lxc.mount.entry: /mnt/pve/zima data none bind,create=dir\n"
        )

        reconciled = reconcile.reconcile_lxc_config_text(
            original,
            [
                "lxc.idmap: u 0 100000 13000",
                "lxc.mount.entry: /dev/net/tun dev/net/tun none bind,create=file",
                "lxc.mount.entry: /mnt/pve/zima data none bind,create=dir",
            ],
        )

        self.assertNotIn("# BEGIN HAAC MANAGED LXC HARDWARE", reconciled)
        self.assertNotIn("# END HAAC MANAGED LXC HARDWARE", reconciled)
        self.assertIn(
            "arch: amd64\n"
            "unprivileged: 1\n"
            "lxc.idmap: u 0 100000 13000\n"
            "lxc.mount.entry: /dev/net/tun dev/net/tun none bind,create=file\n"
            "lxc.mount.entry: /mnt/pve/zima data none bind,create=dir\n",
            reconciled,
        )

    def test_reconcile_clean_managed_lines_are_unchanged(self) -> None:
        original = (
            "#K3s Master Node (Control Plane + Traefik) (HaaC v3)\n"
            "arch: amd64\n"
            "unprivileged: 1\n"
            "lxc.idmap: u 0 100000 13000\n"
            "lxc.mount.entry: /dev/net/tun dev/net/tun none bind,create=file\n"
            "lxc.mount.entry: /mnt/pve/zima data none bind,create=dir\n"
        )

        reconciled = reconcile.reconcile_lxc_config_text(
            original,
            [
                "lxc.idmap: u 0 100000 13000",
                "lxc.mount.entry: /dev/net/tun dev/net/tun none bind,create=file",
                "lxc.mount.entry: /mnt/pve/zima data none bind,create=dir",
            ],
        )

        self.assertEqual(reconciled, original)

    def test_reconcile_removes_stale_nas_mount_path(self) -> None:
        original = (
            "#K3s Worker Node (HaaC v3)\n"
            "arch: amd64\n"
            "unprivileged: 1\n"
            "lxc.mount.entry: /mnt/pve/old data none bind,create=dir\n"
        )

        reconciled = reconcile.reconcile_lxc_config_text(
            original,
            ["lxc.mount.entry: /mnt/pve/new data none bind,create=dir"],
        )

        self.assertNotIn("/mnt/pve/old", reconciled)
        self.assertIn("/mnt/pve/new", reconciled)
        self.assertEqual(
            reconciled,
            (
                "#K3s Worker Node (HaaC v3)\n"
                "arch: amd64\n"
                "unprivileged: 1\n"
                "lxc.mount.entry: /mnt/pve/new data none bind,create=dir\n"
            ),
        )


if __name__ == "__main__":
    unittest.main()
