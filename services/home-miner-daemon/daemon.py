#!/usr/bin/env python3
"""
Zend Home Miner Daemon

LAN-only control service for milestone 1.
Binds to 127.0.0.1 only for local development/testing.
Production deployment uses the local network interface.

This is a milestone 1 simulator that exposes the same contract
a real miner backend will use.
"""

import json
import os
import socketserver
import threading
import time
from datetime import datetime, timezone
from enum import Enum
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from typing import Optional


def default_state_dir() -> str:
    """Resolve the repo-root state directory independent of cwd."""
    return str(Path(__file__).resolve().parents[2] / "state")


STATE_DIR = os.environ.get("ZEND_STATE_DIR", default_state_dir())
os.makedirs(STATE_DIR, exist_ok=True)
MINER_STATE_FILE = os.path.join(STATE_DIR, "miner-state.json")

# LAN-only binding (127.0.0.1 for dev, can be configured for LAN)
BIND_HOST = os.environ.get('ZEND_BIND_HOST', '127.0.0.1')
BIND_PORT = int(os.environ.get('ZEND_BIND_PORT', 8080))


class MinerMode(str, Enum):
    PAUSED = "paused"
    BALANCED = "balanced"
    PERFORMANCE = "performance"


class MinerStatus(str, Enum):
    RUNNING = "running"
    STOPPED = "stopped"
    OFFLINE = "offline"
    ERROR = "error"


def normalize_wire_payload(value):
    """Convert Enum-backed daemon state into JSON wire values."""
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, dict):
        return {key: normalize_wire_payload(item) for key, item in value.items()}
    if isinstance(value, list):
        return [normalize_wire_payload(item) for item in value]
    return value


class MinerSimulator:
    """
    Miner simulator for milestone 1.

    Exposes the same contract a real miner will use:
    - status: current miner state
    - start: start mining
    - stop: stop mining
    - set_mode: change operating mode
    - health: health check
    """

    def __init__(self):
        self._lock = threading.Lock()
        self._status = MinerStatus.STOPPED
        self._mode = MinerMode.PAUSED
        self._hashrate_hs = 0
        self._temperature = 45.0
        self._uptime_seconds = 0
        self._started_at: Optional[float] = None
        self._load_state()

    def _load_state(self):
        if not os.path.exists(MINER_STATE_FILE):
            return

        with open(MINER_STATE_FILE, "r") as f:
            data = json.load(f)

        self._status = MinerStatus(data.get("status", MinerStatus.STOPPED.value))
        self._mode = MinerMode(data.get("mode", MinerMode.PAUSED.value))
        self._hashrate_hs = data.get("hashrate_hs", 0)
        self._temperature = data.get("temperature", 45.0)
        self._uptime_seconds = data.get("uptime_seconds", 0)
        self._started_at = data.get("started_at")

    def _save_state(self):
        with open(MINER_STATE_FILE, "w") as f:
            json.dump(
                {
                    "status": self._status.value,
                    "mode": self._mode.value,
                    "hashrate_hs": self._hashrate_hs,
                    "temperature": self._temperature,
                    "uptime_seconds": self._uptime_seconds,
                    "started_at": self._started_at,
                },
                f,
                indent=2,
            )

    @property
    def status(self) -> MinerStatus:
        return self._status

    @property
    def mode(self) -> MinerMode:
        return self._mode

    @property
    def health(self) -> dict:
        with self._lock:
            self._load_state()
            if self._started_at:
                self._uptime_seconds = int(time.time() - self._started_at)
                self._save_state()

        return {
            "healthy": self._status != MinerStatus.ERROR,
            "temperature": self._temperature,
            "uptime_seconds": self._uptime_seconds,
        }

    def start(self) -> dict:
        with self._lock:
            self._load_state()
            if self._status == MinerStatus.RUNNING:
                return {"success": False, "error": "already_running"}

            self._status = MinerStatus.RUNNING
            self._started_at = time.time()

            # Simulate different hash rates based on mode
            if self._mode == MinerMode.PAUSED:
                self._hashrate_hs = 0
            elif self._mode == MinerMode.BALANCED:
                self._hashrate_hs = 50000
            else:  # PERFORMANCE
                self._hashrate_hs = 150000

            self._save_state()

            return {"success": True, "status": self._status.value}

    def stop(self) -> dict:
        with self._lock:
            self._load_state()
            if self._status == MinerStatus.STOPPED:
                return {"success": False, "error": "already_stopped"}

            self._status = MinerStatus.STOPPED
            self._hashrate_hs = 0
            self._uptime_seconds = 0
            self._started_at = None
            self._save_state()
            return {"success": True, "status": self._status.value}

    def set_mode(self, mode: str) -> dict:
        with self._lock:
            self._load_state()
            try:
                new_mode = MinerMode(mode)
            except ValueError:
                return {"success": False, "error": "invalid_mode"}

            self._mode = new_mode

            # Update hashrate based on new mode
            if self._status == MinerStatus.RUNNING:
                if new_mode == MinerMode.PAUSED:
                    self._hashrate_hs = 0
                elif new_mode == MinerMode.BALANCED:
                    self._hashrate_hs = 50000
                else:  # PERFORMANCE
                    self._hashrate_hs = 150000

            self._save_state()

            return {"success": True, "mode": self._mode.value}

    def get_snapshot(self) -> dict:
        """Returns the cached status object for clients."""
        with self._lock:
            self._load_state()
            if self._started_at:
                self._uptime_seconds = int(time.time() - self._started_at)
                self._save_state()

            return {
                "status": self._status.value,
                "mode": self._mode.value,
                "hashrate_hs": self._hashrate_hs,
                "temperature": self._temperature,
                "uptime_seconds": self._uptime_seconds,
                "freshness": datetime.now(timezone.utc).isoformat(),
            }


# Global miner instance
miner = MinerSimulator()


class GatewayHandler(BaseHTTPRequestHandler):
    """HTTP handler for gateway API."""

    def log_message(self, format, *args):
        """Suppress default logging."""
        pass

    def _send_json(self, status: int, data: dict):
        self.send_response(status)
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps(normalize_wire_payload(data)).encode())

    def do_GET(self):
        if self.path == '/health':
            self._send_json(200, miner.health)
        elif self.path == '/status':
            self._send_json(200, miner.get_snapshot())
        else:
            self._send_json(404, {"error": "not_found"})

    def do_POST(self):
        content_length = int(self.headers.get('Content-Length', 0))
        body = self.rfile.read(content_length)

        try:
            data = json.loads(body) if body else {}
        except json.JSONDecodeError:
            self._send_json(400, {"error": "invalid_json"})
            return

        if self.path == '/miner/start':
            result = miner.start()
            self._send_json(200 if result["success"] else 400, result)
        elif self.path == '/miner/stop':
            result = miner.stop()
            self._send_json(200 if result["success"] else 400, result)
        elif self.path == '/miner/set_mode':
            mode = data.get('mode')
            if not mode:
                self._send_json(400, {"error": "missing_mode"})
                return
            result = miner.set_mode(mode)
            self._send_json(200 if result["success"] else 400, result)
        else:
            self._send_json(404, {"error": "not_found"})


class ThreadedHTTPServer(socketserver.ThreadingMixIn, HTTPServer):
    """Threaded HTTP server for handling concurrent requests."""
    allow_reuse_address = True


def dispatch_local(method: str, path: str, data: Optional[dict] = None) -> tuple[int, dict]:
    """Handle the daemon contract in-process for proof environments."""
    if method == "GET" and path == "/health":
        return 200, normalize_wire_payload(miner.health)
    if method == "GET" and path == "/status":
        return 200, normalize_wire_payload(miner.get_snapshot())
    if method == "POST" and path == "/miner/start":
        result = miner.start()
        return (200 if result["success"] else 400), normalize_wire_payload(result)
    if method == "POST" and path == "/miner/stop":
        result = miner.stop()
        return (200 if result["success"] else 400), normalize_wire_payload(result)
    if method == "POST" and path == "/miner/set_mode":
        mode = (data or {}).get("mode")
        if not mode:
            return 400, {"error": "missing_mode"}
        result = miner.set_mode(mode)
        return (200 if result["success"] else 400), normalize_wire_payload(result)
    return 404, {"error": "not_found"}


def run_server(host: str = BIND_HOST, port: int = BIND_PORT):
    """Run the gateway server."""
    server = ThreadedHTTPServer((host, port), GatewayHandler)
    print(f"Zend Home Miner Daemon starting on {host}:{port}")
    print(f"LISTENING ON: {host}:{port}")
    print("Press Ctrl+C to stop")

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down...")
        server.shutdown()


if __name__ == '__main__':
    run_server()
