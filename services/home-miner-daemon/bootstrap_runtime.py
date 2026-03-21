#!/usr/bin/env python3
"""
Bootstrap/runtime helpers for the home-miner daemon.

These helpers are intentionally pure procfs readers so the bootstrap shell
script can reason about stale PID files and port ownership without needing
network probes or privileged tooling such as lsof/fuser.
"""

from __future__ import annotations

import argparse
import json
import os
import socket
from dataclasses import asdict, dataclass
from pathlib import Path


PROC_ROOT = Path(os.environ.get("ZEND_PROC_ROOT", "/proc"))


@dataclass
class ListenerProcess:
    pid: int
    cmdline: str
    inode: str
    managed: bool
    owned: bool


def _read_text(path: Path) -> str | None:
    try:
        return path.read_text().strip()
    except OSError:
        return None


def _read_bytes(path: Path) -> bytes | None:
    try:
        return path.read_bytes()
    except OSError:
        return None


def _pid_state(pid: int, proc_root: Path = PROC_ROOT) -> str | None:
    stat_text = _read_text(proc_root / str(pid) / "stat")
    if not stat_text:
        return None

    try:
        _prefix, remainder = stat_text.split(") ", 1)
    except ValueError:
        return None

    parts = remainder.split()
    if not parts:
        return None
    return parts[0]


def pid_is_active(pid: int, proc_root: Path = PROC_ROOT) -> bool:
    """Treat missing and zombie processes as inactive."""
    state = _pid_state(pid, proc_root=proc_root)
    return state not in {None, "Z", "X"}


def _host_to_proc_hex(host: str) -> str:
    packed = socket.inet_aton(host)
    return "".join(f"{byte:02X}" for byte in reversed(packed))


def _conflicts_with_bind_host(bind_host: str, local_host_hex: str) -> bool:
    if bind_host == "0.0.0.0":
        return True
    return local_host_hex in {_host_to_proc_hex(bind_host), "00000000"}


def _listening_inodes(bind_host: str, port: int, proc_root: Path = PROC_ROOT) -> set[str]:
    tcp_path = proc_root / "net" / "tcp"
    tcp_text = _read_text(tcp_path)
    if not tcp_text:
        return set()

    port_hex = f"{port:04X}"
    inodes: set[str] = set()
    for line in tcp_text.splitlines()[1:]:
        parts = line.split()
        if len(parts) < 10:
            continue
        local_address = parts[1]
        state = parts[3]
        inode = parts[9]
        if state != "0A":
            continue
        try:
            local_host_hex, local_port_hex = local_address.split(":")
        except ValueError:
            continue
        if local_port_hex != port_hex:
            continue
        if not _conflicts_with_bind_host(bind_host, local_host_hex):
            continue
        inodes.add(inode)
    return inodes


def _read_cmdline(pid: int, proc_root: Path = PROC_ROOT) -> str:
    args = _read_cmdline_args(pid, proc_root=proc_root)
    if not args:
        return ""
    return " ".join(args)


def _read_cmdline_args(pid: int, proc_root: Path = PROC_ROOT) -> list[str]:
    cmdline = _read_bytes(proc_root / str(pid) / "cmdline")
    if not cmdline:
        return []
    return [part.decode(errors="replace") for part in cmdline.split(b"\0") if part]


def _read_cwd(pid: int, proc_root: Path = PROC_ROOT) -> str | None:
    try:
        return os.readlink(proc_root / str(pid) / "cwd")
    except OSError:
        return None


def _resolve_path(path: str | Path | None) -> Path | None:
    if path is None:
        return None
    try:
        return Path(path).resolve()
    except OSError:
        return Path(path)


def _same_path(left: str | Path | None, right: str | Path | None) -> bool:
    left_path = _resolve_path(left)
    right_path = _resolve_path(right)
    if left_path is None or right_path is None:
        return False
    return left_path == right_path


def _looks_like_daemon_dir(path: str | Path | None) -> bool:
    daemon_dir = _resolve_path(path)
    if daemon_dir is None:
        return False
    if daemon_dir.name != "home-miner-daemon" or daemon_dir.parent.name != "services":
        return False
    return all((daemon_dir / marker).exists() for marker in ("daemon.py", "cli.py", "store.py"))


def process_matches_daemon(pid: int, daemon_dir: str, proc_root: Path = PROC_ROOT) -> bool:
    daemon_dir_path = Path(daemon_dir).resolve()
    daemon_script = daemon_dir_path / "daemon.py"
    for arg in _read_cmdline_args(pid, proc_root=proc_root):
        arg_path = _resolve_path(arg)
        if arg_path is not None and arg_path == daemon_script:
            return True

    cwd = _read_cwd(pid, proc_root=proc_root)
    return _same_path(cwd, daemon_dir_path)


def process_matches_daemon_family(pid: int, proc_root: Path = PROC_ROOT) -> bool:
    args = _read_cmdline_args(pid, proc_root=proc_root)
    if not any(Path(arg).name == "daemon.py" for arg in args):
        return False

    for arg in args:
        arg_path = _resolve_path(arg)
        if arg_path is None:
            continue
        if arg_path.name == "daemon.py" and _looks_like_daemon_dir(arg_path.parent):
            return True

    cwd = _read_cwd(pid, proc_root=proc_root)
    return _looks_like_daemon_dir(cwd)


def list_listener_processes(
    bind_host: str,
    port: int,
    daemon_dir: str,
    proc_root: Path = PROC_ROOT,
) -> list[ListenerProcess]:
    inodes = _listening_inodes(bind_host, port, proc_root=proc_root)
    if not inodes:
        return []

    listeners: list[ListenerProcess] = []
    seen_pids: set[int] = set()
    for proc_entry in proc_root.iterdir():
        if not proc_entry.name.isdigit():
            continue
        pid = int(proc_entry.name)
        if pid in seen_pids:
            continue
        fd_dir = proc_entry / "fd"
        try:
            fds = list(fd_dir.iterdir())
        except OSError:
            continue
        for fd_path in fds:
            try:
                target = os.readlink(fd_path)
            except OSError:
                continue
            if not target.startswith("socket:[") or not target.endswith("]"):
                continue
            inode = target.removeprefix("socket:[").removesuffix("]")
            if inode not in inodes:
                continue
            listeners.append(
                ListenerProcess(
                    pid=pid,
                    cmdline=_read_cmdline(pid, proc_root=proc_root),
                    inode=inode,
                    managed=process_matches_daemon_family(pid, proc_root=proc_root),
                    owned=process_matches_daemon(pid, daemon_dir, proc_root=proc_root),
                )
            )
            seen_pids.add(pid)
            break

    listeners.sort(key=lambda listener: listener.pid)
    return listeners


def find_owned_listener_process(
    bind_host: str,
    port: int,
    daemon_dir: str,
    proc_root: Path = PROC_ROOT,
) -> ListenerProcess | None:
    for listener in list_listener_processes(
        bind_host,
        port,
        daemon_dir,
        proc_root=proc_root,
    ):
        if listener.owned:
            return listener
    return None


def list_managed_listener_processes(
    bind_host: str,
    port: int,
    daemon_dir: str,
    proc_root: Path = PROC_ROOT,
) -> list[ListenerProcess]:
    return [
        listener
        for listener in list_listener_processes(
            bind_host,
            port,
            daemon_dir,
            proc_root=proc_root,
        )
        if listener.managed
    ]


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Bootstrap runtime helpers")
    subparsers = parser.add_subparsers(dest="command", required=True)

    pid_active = subparsers.add_parser("pid-active", help="Exit zero for active PID")
    pid_active.add_argument("pid", type=int)

    listener_report = subparsers.add_parser(
        "listener-report",
        help="Print JSON describing processes that own a bind host/port",
    )
    listener_report.add_argument("host")
    listener_report.add_argument("port", type=int)
    listener_report.add_argument("daemon_dir")

    owned_listener = subparsers.add_parser(
        "owned-listener-pid",
        help="Print PID if the configured daemon already owns the port",
    )
    owned_listener.add_argument("host")
    owned_listener.add_argument("port", type=int)
    owned_listener.add_argument("daemon_dir")

    managed_listener = subparsers.add_parser(
        "managed-listener-pids",
        help="Print listener PIDs for reclaimable Zend daemon processes",
    )
    managed_listener.add_argument("host")
    managed_listener.add_argument("port", type=int)
    managed_listener.add_argument("daemon_dir")

    return parser


def main() -> int:
    parser = _build_parser()
    args = parser.parse_args()

    if args.command == "pid-active":
        return 0 if pid_is_active(args.pid) else 1

    if args.command == "listener-report":
        listeners = list_listener_processes(args.host, args.port, args.daemon_dir)
        print(json.dumps({"listeners": [asdict(listener) for listener in listeners]}))
        return 0

    if args.command == "owned-listener-pid":
        listener = find_owned_listener_process(args.host, args.port, args.daemon_dir)
        if listener is None:
            return 1
        print(listener.pid)
        return 0

    if args.command == "managed-listener-pids":
        listeners = list_managed_listener_processes(args.host, args.port, args.daemon_dir)
        if not listeners:
            return 1
        for listener in listeners:
            print(listener.pid)
        return 0

    parser.error(f"unsupported command: {args.command}")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
