#!/usr/bin/env python3
"""
Zend Home Miner Daemon

LAN-only control service for milestone 1.
Binds to 127.0.0.1 only for local development/testing.
Production deployment uses the local network interface.

This is a milestone 1 simulator that exposes the same contract
a real miner backend will use.
"""

import socketserver
import json
import os
import sys
import threading
import time
from datetime import datetime, timezone
from enum import Enum
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from typing import Optional

from store import get_pairing_by_token
import spine


def default_state_dir() -> str:
    """Resolve the repo-root state directory independent of cwd."""
    return str(Path(__file__).resolve().parents[2] / "state")


STATE_DIR = os.environ.get("ZEND_STATE_DIR", default_state_dir())
os.makedirs(STATE_DIR, exist_ok=True)

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
        self._status = MinerStatus.STOPPED
        self._mode = MinerMode.PAUSED
        self._hashrate_hs = 0
        self._temperature = 45.0
        self._uptime_seconds = 0
        self._started_at: Optional[float] = None
        self._lock = threading.Lock()

    @property
    def status(self) -> MinerStatus:
        return self._status

    @property
    def mode(self) -> MinerMode:
        return self._mode

    @property
    def health(self) -> dict:
        return {
            "healthy": self._status != MinerStatus.ERROR,
            "temperature": self._temperature,
            "uptime_seconds": self._uptime_seconds,
        }

    def start(self) -> dict:
        with self._lock:
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

            return {"success": True, "status": self._status}

    def stop(self) -> dict:
        with self._lock:
            if self._status == MinerStatus.STOPPED:
                return {"success": False, "error": "already_stopped"}

            self._status = MinerStatus.STOPPED
            self._hashrate_hs = 0
            return {"success": True, "status": self._status}

    def set_mode(self, mode: str) -> dict:
        with self._lock:
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

            return {"success": True, "mode": self._mode}

    def get_snapshot(self) -> dict:
        """Returns the cached status object for clients."""
        with self._lock:
            if self._started_at:
                self._uptime_seconds = int(time.time() - self._started_at)

            return {
                "status": self._status,
                "mode": self._mode,
                "hashrate_hs": self._hashrate_hs,
                "temperature": self._temperature,
                "uptime_seconds": self._uptime_seconds,
                "freshness": datetime.now(timezone.utc).isoformat(),
            }


# Global miner instance
miner = MinerSimulator()


def _response(status: int, data: dict) -> tuple[int, dict]:
    """Construct a request handler response."""
    return status, data


def _error_response(status: int, error: str, message: str, code: str) -> tuple[int, dict]:
    """Return a structured error payload aligned with the error taxonomy."""
    return _response(
        status,
        {
            "success": False,
            "error": error,
            "code": code,
            "message": message,
        },
    )


def _get_header(headers, name: str) -> Optional[str]:
    """Read an HTTP header from either a real request object or a test mapping."""
    if not headers:
        return None
    value = headers.get(name)
    if value is None:
        value = headers.get(name.lower())
    return value


def _extract_bearer_token(headers) -> Optional[str]:
    """Extract the bearer token used to identify a paired device."""
    authorization = _get_header(headers, 'Authorization')
    if not authorization:
        return None

    scheme, _, token = authorization.partition(' ')
    if scheme.lower() != 'bearer' or not token.strip():
        return None

    return token.strip()


def _authorize(headers, required_capabilities: tuple[str, ...]):
    """Authorize the request against the pairing store."""
    token = _extract_bearer_token(headers)
    if not token:
        return None, _error_response(
            401,
            "unauthorized",
            "Missing bearer token for paired device.",
            "GATEWAY_UNAUTHORIZED",
        )

    pairing = get_pairing_by_token(token)
    if not pairing:
        return None, _error_response(
            401,
            "unauthorized",
            "Unknown paired device.",
            "GATEWAY_UNAUTHORIZED",
        )

    if required_capabilities and not any(
        capability in pairing.capabilities for capability in required_capabilities
    ):
        return pairing, _error_response(
            403,
            "unauthorized",
            "This device lacks the required capability for this action.",
            "GATEWAY_UNAUTHORIZED",
        )

    return pairing, None


def _append_control_receipt(command: str, mode: Optional[str], status: str, pairing) -> None:
    """Append a control receipt for any accepted or rejected command."""
    spine.append_control_receipt(command, mode, status, pairing.principal_id)


def handle_get_request(path: str, headers=None) -> tuple[int, dict]:
    """Pure GET request dispatcher for daemon logic and non-socket verification."""
    if path == '/health':
        return _response(200, miner.health)
    if path == '/status':
        _, error = _authorize(headers, ('observe', 'control'))
        if error:
            return error
        return _response(200, miner.get_snapshot())
    return _response(404, {"error": "not_found"})


def handle_post_request(path: str, data: Optional[dict] = None, headers=None) -> tuple[int, dict]:
    """Pure POST request dispatcher for daemon logic and non-socket verification."""
    data = data or {}

    if path == '/miner/start':
        pairing, error = _authorize(headers, ('control',))
        if error:
            if pairing:
                _append_control_receipt('start', None, 'rejected', pairing)
            return error
        result = miner.start()
        _append_control_receipt('start', None, 'accepted' if result["success"] else 'rejected', pairing)
        return _response(200 if result["success"] else 400, result)

    if path == '/miner/stop':
        pairing, error = _authorize(headers, ('control',))
        if error:
            if pairing:
                _append_control_receipt('stop', None, 'rejected', pairing)
            return error
        result = miner.stop()
        _append_control_receipt('stop', None, 'accepted' if result["success"] else 'rejected', pairing)
        return _response(200 if result["success"] else 400, result)

    if path == '/miner/set_mode':
        pairing, error = _authorize(headers, ('control',))
        mode = data.get('mode')
        if error:
            if pairing:
                _append_control_receipt('set_mode', mode, 'rejected', pairing)
            return error
        if not mode:
            return _response(400, {"error": "missing_mode"})
        result = miner.set_mode(mode)
        _append_control_receipt(
            'set_mode',
            mode,
            'accepted' if result["success"] else 'rejected',
            pairing,
        )
        return _response(200 if result["success"] else 400, result)

    return _response(404, {"error": "not_found"})


class GatewayHandler(BaseHTTPRequestHandler):
    """HTTP handler for gateway API."""

    def log_message(self, format, *args):
        """Suppress default logging."""
        pass

    def _send_json(self, status: int, data: dict):
        self.send_response(status)
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps(data).encode())

    def do_GET(self):
        status, payload = handle_get_request(self.path, self.headers)
        self._send_json(status, payload)

    def do_POST(self):
        content_length = int(self.headers.get('Content-Length', 0))
        body = self.rfile.read(content_length)

        try:
            data = json.loads(body) if body else {}
        except json.JSONDecodeError:
            self._send_json(400, {"error": "invalid_json"})
            return

        status, payload = handle_post_request(self.path, data, self.headers)
        self._send_json(status, payload)


class ThreadedHTTPServer(socketserver.ThreadingMixIn, HTTPServer):
    """Threaded HTTP server for handling concurrent requests."""
    allow_reuse_address = True


def run_server(host: str = BIND_HOST, port: int = BIND_PORT) -> int:
    """Run the gateway server."""
    try:
        server = ThreadedHTTPServer((host, port), GatewayHandler)
    except OSError as exc:
        if exc.errno == 98:
            print(
                f"DAEMON_PORT_IN_USE: Zend Home Miner Daemon could not bind to {host}:{port}",
                file=sys.stderr,
            )
        else:
            print(
                f"DAEMON_BIND_FAILED: Zend Home Miner Daemon could not bind to {host}:{port}: {exc}",
                file=sys.stderr,
            )
        return 1

    print(f"Zend Home Miner Daemon starting on {host}:{port}")
    print(f"LISTENING ON: {host}:{port}")
    print("Press Ctrl+C to stop")

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down...")
        server.shutdown()

    return 0


if __name__ == '__main__':
    raise SystemExit(run_server())
