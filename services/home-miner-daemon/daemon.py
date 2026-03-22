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

# Hermes connection registry: hermes_id -> HermesConnection
# Active connections are stored here for authenticated requests
_hermes_connections: dict[str, "HermesConnection"] = {}

import hermes as _hermes


def _get_hermes_connection_from_request(
    handler: "GatewayHandler",
) -> Optional["HermesConnection"]:
    """
    Extract and validate the Hermes Authorization header.

    Expects: Authorization: Hermes <authority_token>

    Returns the active HermesConnection or None if not authenticated.
    """
    auth_header = handler.headers.get("Authorization", "")
    if not auth_header.startswith("Hermes "):
        return None
    token_str = auth_header[7:].strip()
    if not token_str:
        return None
    try:
        conn = _hermes.connect(token_str)
        _hermes_connections[conn.hermes_id] = conn
        return conn
    except ValueError:
        return None


class GatewayHandler(BaseHTTPRequestHandler):
    """HTTP handler for gateway API including Hermes adapter endpoints."""

    def log_message(self, format, *args):
        """Suppress default logging."""
        pass

    def _send_json(self, status: int, data: dict):
        self.send_response(status)
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps(data).encode())

    def _require_hermes_auth(self) -> Optional["HermesConnection"]:
        """Return HermesConnection or send 401 and return None."""
        conn = _get_hermes_connection_from_request(self)
        if conn is None:
            self._send_json(401, {
                "error": "unauthorized",
                "message": "Valid Hermes authority token required"
            })
        return conn

    # ------------------------------------------------------------------
    # Public gateway endpoints
    # ------------------------------------------------------------------

    def do_GET(self):
        if self.path == '/health':
            self._send_json(200, miner.health)
        elif self.path == '/status':
            self._send_json(200, miner.get_snapshot())
        elif self.path == '/hermes/status':
            conn = self._require_hermes_auth()
            if conn is None:
                return
            try:
                status = _hermes.read_status(conn)
                self._send_json(200, status)
            except PermissionError as e:
                self._send_json(403, {"error": "forbidden", "message": str(e)})
        elif self.path == '/hermes/events':
            conn = self._require_hermes_auth()
            if conn is None:
                return
            try:
                events = _hermes.get_filtered_events(conn, limit=20)
                self._send_json(200, {"events": events})
            except PermissionError as e:
                self._send_json(403, {"error": "forbidden", "message": str(e)})
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

        # ----------------------------------------------------------------
        # Hermes adapter endpoints
        # ----------------------------------------------------------------
        if self.path == '/hermes/pair':
            hermes_id = data.get("hermes_id")
            device_name = data.get("device_name", "hermes-agent")
            if not hermes_id:
                self._send_json(400, {"error": "missing_hermes_id"})
                return

            # Use or create principal
            from store import load_or_create_principal
            principal = load_or_create_principal()

            record = _hermes.pair_hermes(hermes_id, device_name, principal.id)

            # Issue a new token for this pairing
            token_encoded, token_obj = _hermes.issue_hermes_token(
                hermes_id=hermes_id,
                principal_id=principal.id,
                capabilities=_hermes.HERMES_CAPABILITIES,
                ttl_hours=24,
            )

            self._send_json(200, {
                "hermes_id": record["hermes_id"],
                "device_name": record["device_name"],
                "principal_id": record["principal_id"],
                "capabilities": record["capabilities"],
                "paired_at": record["paired_at"],
                "authority_token": token_encoded,
                "expires_at": token_obj.expires_at,
            })
            return

        if self.path == '/hermes/connect':
            token_str = data.get("authority_token")
            if not token_str:
                self._send_json(400, {"error": "missing_authority_token"})
                return
            try:
                conn = _hermes.connect(token_str)
                _hermes_connections[conn.hermes_id] = conn
                self._send_json(200, {
                    "hermes_id": conn.hermes_id,
                    "principal_id": conn.principal_id,
                    "capabilities": conn.capabilities,
                    "connected_at": conn.connected_at,
                    "can_observe": conn.can_observe,
                    "can_summarize": conn.can_summarize,
                })
            except ValueError as e:
                self._send_json(401, {"error": "unauthorized", "message": str(e)})
            return

        if self.path == '/hermes/status':
            conn = self._require_hermes_auth()
            if conn is None:
                return
            try:
                status = _hermes.read_status(conn)
                self._send_json(200, status)
            except PermissionError as e:
                self._send_json(403, {"error": "forbidden", "message": str(e)})
            return

        if self.path == '/hermes/summary':
            conn = self._require_hermes_auth()
            if conn is None:
                return
            summary_text = data.get("summary_text")
            authority_scope = data.get("authority_scope", "observe")
            if not summary_text:
                self._send_json(400, {"error": "missing_summary_text"})
                return
            try:
                result = _hermes.append_summary(conn, summary_text, authority_scope)
                self._send_json(200, result)
            except PermissionError as e:
                self._send_json(403, {"error": "forbidden", "message": str(e)})
            return

        # ----------------------------------------------------------------
        # Miner control endpoints (Hermes can NOT use these)
        # ----------------------------------------------------------------
        if self.path == '/miner/start':
            # Check if request came from Hermes — reject with clear message
            auth_header = self.headers.get("Authorization", "")
            if auth_header.startswith("Hermes "):
                self._send_json(403, {
                    "error": "hermes_unauthorized",
                    "message": "HERMES_UNAUTHORIZED: Hermes cannot issue control commands"
                })
                return
            result = miner.start()
            self._send_json(200 if result["success"] else 400, result)
            return

        if self.path == '/miner/stop':
            auth_header = self.headers.get("Authorization", "")
            if auth_header.startswith("Hermes "):
                self._send_json(403, {
                    "error": "hermes_unauthorized",
                    "message": "HERMES_UNAUTHORIZED: Hermes cannot issue control commands"
                })
                return
            result = miner.stop()
            self._send_json(200 if result["success"] else 400, result)
            return

        if self.path == '/miner/set_mode':
            auth_header = self.headers.get("Authorization", "")
            if auth_header.startswith("Hermes "):
                self._send_json(403, {
                    "error": "hermes_unauthorized",
                    "message": "HERMES_UNAUTHORIZED: Hermes cannot issue control commands"
                })
                return
            mode = data.get('mode')
            if not mode:
                self._send_json(400, {"error": "missing_mode"})
                return
            result = miner.set_mode(mode)
            self._send_json(200 if result["success"] else 400, result)
            return

        self._send_json(404, {"error": "not_found"})


class ThreadedHTTPServer(socketserver.ThreadingMixIn, HTTPServer):
    """Threaded HTTP server for handling concurrent requests."""
    allow_reuse_address = True


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
