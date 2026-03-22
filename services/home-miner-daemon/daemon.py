#!/usr/bin/env python3
"""
Zend Home Miner Daemon

LAN-only control service for milestone 1.
Binds to 127.0.0.1 only for local development/testing.
Production deployment uses the local network interface.

This is a milestone 1 simulator that exposes the same contract
a real miner backend will use.

Hermes Endpoints:
- POST /hermes/pair      : Create Hermes pairing record
- POST /hermes/connect   : Connect with authority token
- GET  /hermes/status    : Read miner status (requires Hermes auth)
- POST /hermes/summary   : Append summary (requires Hermes auth)
- GET  /hermes/events    : Read filtered events (no user_message)
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

# Import hermes adapter (support both module and standalone execution)
try:
    from . import hermes
except ImportError:
    import hermes


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
                "status": self._status.value if isinstance(self._status, MinerStatus) else self._status,
                "mode": self._mode.value if isinstance(self._mode, MinerMode) else self._mode,
                "hashrate_hs": self._hashrate_hs,
                "temperature": self._temperature,
                "uptime_seconds": self._uptime_seconds,
                "freshness": datetime.now(timezone.utc).isoformat(),
            }


# Global miner instance
miner = MinerSimulator()


class GatewayHandler(BaseHTTPRequestHandler):
    """HTTP handler for gateway API."""

    # Track active Hermes connections by hermes_id
    _hermes_connections: dict = {}

    def log_message(self, format, *args):
        """Suppress default logging."""
        pass

    def _send_json(self, status: int, data: dict):
        self.send_response(status)
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps(data).encode())

    def _get_hermes_auth(self) -> Optional[str]:
        """Extract Hermes auth from Authorization header.
        
        Expected format: "Authorization: Hermes <hermes_id>"
        """
        auth_header = self.headers.get('Authorization', '')
        if auth_header.startswith('Hermes '):
            return auth_header[7:]  # Return hermes_id
        return None

    def _require_hermes_auth(self):
        """Require Hermes authentication and return connection.
        
        Returns (connection, None) on success, or sends 403 and returns None.
        """
        hermes_id = self._get_hermes_auth()
        if not hermes_id:
            self._send_json(403, {
                "error": "HERMES_UNAUTHORIZED",
                "message": "Authorization header required: Hermes <hermes_id>"
            })
            return None
        
        connection = self._hermes_connections.get(hermes_id)
        if not connection:
            self._send_json(403, {
                "error": "HERMES_NOT_CONNECTED",
                "message": "Hermes not connected. Use POST /hermes/connect first."
            })
            return None
        
        return connection

    def do_GET(self):
        # Hermes endpoints
        if self.path == '/hermes/status':
            connection = self._require_hermes_auth()
            if not connection:
                return
            try:
                status = hermes.read_status(connection)
                self._send_json(200, status)
            except PermissionError as e:
                self._send_json(403, {"error": "HERMES_UNAUTHORIZED", "message": str(e)})
            return

        elif self.path == '/hermes/events':
            connection = self._require_hermes_auth()
            if not connection:
                return
            events = hermes.get_filtered_events(connection)
            self._send_json(200, {
                "events": [
                    {
                        "id": e.id,
                        "kind": e.kind,
                        "payload": e.payload,
                        "created_at": e.created_at
                    }
                    for e in events
                ],
                "count": len(events)
            })
            return

        # Public endpoints
        elif self.path == '/health':
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

        # Hermes endpoints
        if self.path == '/hermes/pair':
            hermes_id = data.get('hermes_id')
            device_name = data.get('device_name')
            if not hermes_id:
                self._send_json(400, {"error": "missing_hermes_id"})
                return
            try:
                pairing = hermes.pair_hermes(hermes_id, device_name)
                self._send_json(200, {
                    "success": True,
                    "hermes_id": pairing.hermes_id,
                    "device_name": pairing.device_name,
                    "capabilities": pairing.capabilities,
                    "paired_at": pairing.paired_at
                })
            except Exception as e:
                self._send_json(400, {"error": str(e)})
            return

        elif self.path == '/hermes/connect':
            token = data.get('authority_token')
            if not token:
                self._send_json(400, {"error": "missing_authority_token"})
                return
            try:
                connection = hermes.connect(token)
                self._hermes_connections[connection.hermes_id] = connection
                self._send_json(200, {
                    "success": True,
                    "hermes_id": connection.hermes_id,
                    "capabilities": connection.capabilities,
                    "connected_at": connection.connected_at,
                    "expires_at": connection.token_expires_at
                })
            except ValueError as e:
                self._send_json(401, {"error": "HERMES_AUTH_FAILED", "message": str(e)})
            return

        elif self.path == '/hermes/summary':
            connection = self._require_hermes_auth()
            if not connection:
                return
            summary_text = data.get('summary_text')
            authority_scope = data.get('authority_scope', 'observe')
            if not summary_text:
                self._send_json(400, {"error": "missing_summary_text"})
                return
            try:
                event = hermes.append_summary(connection, summary_text, authority_scope)
                self._send_json(200, {
                    "appended": True,
                    "event_id": event.id,
                    "created_at": event.created_at
                })
            except PermissionError as e:
                self._send_json(403, {"error": "HERMES_UNAUTHORIZED", "message": str(e)})
            except ValueError as e:
                self._send_json(400, {"error": str(e)})
            return

        # Control endpoints - Hermes CANNOT use these
        elif self.path == '/miner/start':
            if self._get_hermes_auth():
                self._send_json(403, {
                    "error": "HERMES_UNAUTHORIZED",
                    "message": "Hermes cannot issue control commands"
                })
                return
            result = miner.start()
            self._send_json(200 if result["success"] else 400, result)

        elif self.path == '/miner/stop':
            if self._get_hermes_auth():
                self._send_json(403, {
                    "error": "HERMES_UNAUTHORIZED",
                    "message": "Hermes cannot issue control commands"
                })
                return
            result = miner.stop()
            self._send_json(200 if result["success"] else 400, result)

        elif self.path == '/miner/set_mode':
            if self._get_hermes_auth():
                self._send_json(403, {
                    "error": "HERMES_UNAUTHORIZED",
                    "message": "Hermes cannot issue control commands"
                })
                return
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
