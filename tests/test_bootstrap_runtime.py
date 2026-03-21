#!/usr/bin/env python3

import importlib
import os
import sys
import tempfile
import unittest
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[1]
DAEMON_DIR = ROOT_DIR / "services" / "home-miner-daemon"

if str(DAEMON_DIR) not in sys.path:
    sys.path.insert(0, str(DAEMON_DIR))


bootstrap_runtime = importlib.import_module("bootstrap_runtime")


class BootstrapRuntimeTest(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.proc_root = Path(self.temp_dir.name) / "proc"
        (self.proc_root / "net").mkdir(parents=True)
        (self.proc_root / "net" / "tcp").write_text(
            "  sl  local_address rem_address   st tx_queue rx_queue tr tm->when retrnsmt"
            "   uid  timeout inode\n"
        )
        self.daemon_dir = Path(self.temp_dir.name) / "workspace" / "services" / "home-miner-daemon"
        self.daemon_dir.mkdir(parents=True)
        for filename in ("daemon.py", "cli.py", "store.py"):
            (self.daemon_dir / filename).write_text("# test marker\n")

    def _append_tcp_listener(self, local_host_hex: str, port: int, inode: str):
        tcp_path = self.proc_root / "net" / "tcp"
        with tcp_path.open("a") as handle:
            handle.write(
                f"   0: {local_host_hex}:{port:04X} 00000000:0000 0A 00000000:00000000 "
                f"00:00000000 00000000  1000        0 {inode} 1 0000000000000000 100 0 0 10 0\n"
            )

    def _write_process(
        self,
        pid: int,
        *,
        state: str = "S",
        cmdline: list[str] | None = None,
        cwd: Path | None = None,
        socket_inode: str | None = None,
    ):
        proc_dir = self.proc_root / str(pid)
        fd_dir = proc_dir / "fd"
        fd_dir.mkdir(parents=True)
        (proc_dir / "stat").write_text(
            f"{pid} (python3) {state} 1 1 1 0 -1 0 0 0 0 0 0 0 0 0 20 0 1 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0\n"
        )
        if cmdline is None:
            cmdline = ["python3"]
        (proc_dir / "cmdline").write_bytes(b"\0".join(arg.encode() for arg in cmdline) + b"\0")
        os.symlink(str(cwd or self.daemon_dir), proc_dir / "cwd")
        if socket_inode is not None:
            os.symlink(f"socket:[{socket_inode}]", fd_dir / "0")

    def test_pid_is_active_rejects_zombies(self):
        self._write_process(1234, state="S")
        self._write_process(4321, state="Z")

        self.assertTrue(bootstrap_runtime.pid_is_active(1234, proc_root=self.proc_root))
        self.assertFalse(bootstrap_runtime.pid_is_active(4321, proc_root=self.proc_root))
        self.assertFalse(bootstrap_runtime.pid_is_active(9999, proc_root=self.proc_root))

    def test_list_listener_processes_marks_owned_daemon(self):
        self._append_tcp_listener("0100007F", 18080, "7777")
        self._write_process(
            2222,
            cmdline=["python3", "daemon.py"],
            cwd=self.daemon_dir,
            socket_inode="7777",
        )

        listeners = bootstrap_runtime.list_listener_processes(
            "127.0.0.1",
            18080,
            str(self.daemon_dir),
            proc_root=self.proc_root,
        )

        self.assertEqual(len(listeners), 1)
        self.assertEqual(listeners[0].pid, 2222)
        self.assertTrue(listeners[0].managed)
        self.assertTrue(listeners[0].owned)
        self.assertIn("daemon.py", listeners[0].cmdline)

    def test_list_listener_processes_exposes_foreign_port_owner(self):
        self._append_tcp_listener("00000000", 8080, "8888")
        self._write_process(
            3333,
            cmdline=["python3", "foreign-service.py"],
            cwd=self.daemon_dir.parent,
            socket_inode="8888",
        )

        listeners = bootstrap_runtime.list_listener_processes(
            "127.0.0.1",
            8080,
            str(self.daemon_dir),
            proc_root=self.proc_root,
        )

        self.assertEqual(len(listeners), 1)
        self.assertEqual(listeners[0].pid, 3333)
        self.assertFalse(listeners[0].managed)
        self.assertFalse(listeners[0].owned)

    def test_find_owned_listener_ignores_other_specific_interfaces(self):
        self._append_tcp_listener("0201A8C0", 8080, "9999")
        self._write_process(
            4444,
            cmdline=["python3", "daemon.py"],
            cwd=self.daemon_dir,
            socket_inode="9999",
        )

        listener = bootstrap_runtime.find_owned_listener_process(
            "127.0.0.1",
            8080,
            str(self.daemon_dir),
            proc_root=self.proc_root,
        )

        self.assertIsNone(listener)

    def test_list_listener_processes_marks_other_worktree_daemon_as_managed(self):
        other_daemon_dir = (
            Path(self.temp_dir.name) / "other-worktree" / "services" / "home-miner-daemon"
        )
        other_daemon_dir.mkdir(parents=True)
        for filename in ("daemon.py", "cli.py", "store.py"):
            (other_daemon_dir / filename).write_text("# test marker\n")

        self._append_tcp_listener("0100007F", 18080, "4242")
        self._write_process(
            5555,
            cmdline=["python3", "daemon.py"],
            cwd=other_daemon_dir,
            socket_inode="4242",
        )

        listeners = bootstrap_runtime.list_listener_processes(
            "127.0.0.1",
            18080,
            str(self.daemon_dir),
            proc_root=self.proc_root,
        )

        self.assertEqual(len(listeners), 1)
        self.assertEqual(listeners[0].pid, 5555)
        self.assertTrue(listeners[0].managed)
        self.assertFalse(listeners[0].owned)

        managed = bootstrap_runtime.list_managed_listener_processes(
            "127.0.0.1",
            18080,
            str(self.daemon_dir),
            proc_root=self.proc_root,
        )

        self.assertEqual([listener.pid for listener in managed], [5555])


if __name__ == "__main__":
    unittest.main()
