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
from typing import Optional, Dict

# Import hermes adapter (lives in the same package)
try:
    import hermes as hermes_adapter
except ImportError:
    hermes_adapter = None


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


class GatewayHandler(BaseHTTPRequestHandler):
    """HTTP handler for gateway API."""

    # In-memory connection store for Hermes sessions (production would use secure session tokens)
    _hermes_connections: Dict[str, 'hermes_adapter.HermesConnection'] = {}

    def log_message(self, format, *args):
        """Suppress default logging."""
        pass

    def _send_json(self, status: int, data: dict):
        self.send_response(status)
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps(data).encode())

    def _parse_hermes_auth(self):
        """
        Parse the Hermes Authorization header.

        Format: "Authorization: Hermes <hermes_id>"
        Returns the hermes_id if valid, None otherwise.
        """
        auth_header = self.headers.get('Authorization', '')
        if not auth_header.startswith('Hermes '):
            return None
        return auth_header[7:].strip()

    def _require_hermes_connection(self):
        """
        Extract hermes_id from Authorization header and return the active connection.
        Returns (connection, hermes_id) on success, or (error_dict, None) on failure.
        """
        hermes_id = self._parse_hermes_auth()
        if not hermes_id:
            return {"error": "hermes_unauthorized", "message": "Missing Hermes Authorization header"}, None

        conn = self._hermes_connections.get(hermes_id)
        if not conn:
            return {"error": "hermes_not_connected", "message": f"Hermes {hermes_id} is not connected. Call POST /hermes/connect first."}, None

        return None, conn

    def do_GET(self):
        # Hermes event filtering endpoint
        if self.path.startswith('/hermes/events'):
            err, conn = self._require_hermes_connection()
            if err:
                self._send_json(403, err)
                return

            try:
                events = hermes_adapter.get_filtered_events(conn)
                self._send_json(200, {"events": events})
            except Exception as e:
                self._send_json(500, {"error": "internal_error", "message": str(e)})
            return

        # Hermes status endpoint
        if self.path == '/hermes/status':
            err, conn = self._require_hermes_connection()
            if err:
                self._send_json(403, err)
                return

            try:
                status = hermes_adapter.read_status(conn)
                self._send_json(200, status)
            except PermissionError as e:
                self._send_json(403, {"error": "hermes_unauthorized", "message": str(e)})
            except Exception as e:
                self._send_json(500, {"error": "internal_error", "message": str(e)})
            return

        # Hermes connection state endpoint
        if self.path == '/hermes/connection':
            hermes_id = self._parse_hermes_auth()
            if not hermes_id:
                self._send_json(401, {"error": "hermes_unauthorized"})
                return
            conn = self._hermes_connections.get(hermes_id)
            if conn:
                self._send_json(200, conn.to_dict())
            else:
                self._send_json(404, {"error": "hermes_not_connected"})
            return

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

        # Hermes pairing endpoint
        if self.path == '/hermes/pair':
            hermes_id = data.get('hermes_id')
            device_name = data.get('device_name', 'hermes-agent')
            if not hermes_id:
                self._send_json(400, {"error": "missing_hermes_id", "message": "hermes_id is required"})
                return

            try:
                pairing = hermes_adapter.pair_hermes(hermes_id, device_name)
                self._send_json(200, {
                    "hermes_id": pairing.hermes_id,
                    "device_name": pairing.device_name,
                    "capabilities": pairing.capabilities,
                    "paired_at": pairing.paired_at,
                    "token_expires_at": pairing.token_expires_at,
                    "authority_token": pairing.hermes_id,  # Token is the hermes_id for simple lookup
                })
            except Exception as e:
                self._send_json(500, {"error": "internal_error", "message": str(e)})
            return

        # Hermes connect endpoint (validates authority token)
        if self.path == '/hermes/connect':
            authority_token = data.get('authority_token')
            if not authority_token:
                self._send_json(400, {"error": "missing_authority_token", "message": "authority_token is required"})
                return

            try:
                conn = hermes_adapter.connect(authority_token)
                # Store connection in session store
                self._hermes_connections[conn.hermes_id] = conn
                self._send_json(200, {
                    "connected": True,
                    "hermes_id": conn.hermes_id,
                    "principal_id": conn.principal_id,
                    "capabilities": conn.capabilities,
                    "connected_at": conn.connected_at,
                    "token_expires_at": conn.token_expires_at,
                })
            except ValueError as e:
                self._send_json(401, {"error": "hermes_invalid_token", "message": str(e)})
            except Exception as e:
                self._send_json(500, {"error": "internal_error", "message": str(e)})
            return

        # Hermes append summary endpoint
        if self.path == '/hermes/summary':
            err, conn = self._require_hermes_connection()
            if err:
                self._send_json(403, err)
                return

            summary_text = data.get('summary_text')
            authority_scope = data.get('authority_scope')

            try:
                result = hermes_adapter.append_summary(conn, summary_text, authority_scope)
                self._send_json(200, result)
            except PermissionError as e:
                self._send_json(403, {"error": "hermes_unauthorized", "message": str(e)})
            except ValueError as e:
                self._send_json(400, {"error": "hermes_invalid_summary", "message": str(e)})
            except Exception as e:
                self._send_json(500, {"error": "internal_error", "message": str(e)})
            return

        if self.path == '/miner/start':
            # Reject control commands from Hermes auth
            if self._parse_hermes_auth():
                self._send_json(403, {
                    "error": "HERMES_UNAUTHORIZED",
                    "message": "Hermes does not have control capability. Only observe and summarize are allowed."
                })
                return
            result = miner.start()
            self._send_json(200 if result["success"] else 400, result)
        elif self.path == '/miner/stop':
            if self._parse_hermes_auth():
                self._send_json(403, {
                    "error": "HERMES_UNAUTHORIZED",
                    "message": "Hermes does not have control capability. Only observe and summarize are allowed."
                })
                return
            result = miner.stop()
            self._send_json(200 if result["success"] else 400, result)
        elif self.path == '/miner/set_mode':
            if self._parse_hermes_auth():
                self._send_json(403, {
                    "error": "HERMES_UNAUTHORIZED",
                    "message": "Hermes does not have control capability. Only observe and summarize are allowed."
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
