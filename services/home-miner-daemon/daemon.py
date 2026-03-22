#!/usr/bin/env python3
"""
Zend Home Miner Daemon

LAN-only control service for milestone 1.
Binds to 127.0.0.1 only for local development/testing.
Production deployment uses the local network interface.

This is a milestone 1 simulator that exposes the same contract
a real miner backend will use.

Hermes Adapter Endpoints:
- POST /hermes/connect - Accept authority token, return connection status
- POST /hermes/pair - Create Hermes pairing with observe+summarize capabilities
- GET /hermes/status - Read miner status through adapter
- POST /hermes/summary - Append summary to event spine
- GET /hermes/events - Read filtered events (no user_message)
"""

import socketserver
import json
import os
import re
import threading
import time
from datetime import datetime, timezone
from enum import Enum
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from typing import Optional

# Hermes adapter imports
try:
    import hermes as hermes_adapter
except ImportError:
    # Handle case where hermes.py is in same directory
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent))
    import hermes as hermes_adapter


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

    def log_message(self, format, *args):
        """Suppress default logging."""
        pass

    def _send_json(self, status: int, data: dict):
        self.send_response(status)
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps(data).encode())

    def _get_hermes_auth(self) -> tuple[Optional[str], Optional[hermes_adapter.HermesConnection]]:
        """Extract and validate Hermes auth from Authorization header.
        
        Returns:
            Tuple of (hermes_id, connection) if valid, (None, None) if invalid/missing
        """
        auth_header = self.headers.get('Authorization', '')
        
        # Parse "Authorization: Hermes <hermes_id>"
        match = re.match(r'Hermes\s+(.+)', auth_header)
        if not match:
            return None, None
        
        hermes_id = match.group(1).strip()
        
        # Validate the connection
        connection = hermes_adapter.validate_connection_auth(hermes_id)
        if not connection:
            return None, None
        
        return hermes_id, connection

    def _require_hermes_auth(self) -> Optional[hermes_adapter.HermesConnection]:
        """Require valid Hermes auth. Send 401 if invalid, return connection if valid."""
        hermes_id, connection = self._get_hermes_auth()
        
        if connection is None:
            self._send_json(401, {
                "error": "unauthorized",
                "message": "Valid Hermes Authorization header required"
            })
            return None
        
        return connection

    def _require_hermes_capability(self, connection: hermes_adapter.HermesConnection, 
                                    capability: str) -> bool:
        """Check if connection has required capability. Send 403 if not."""
        if capability not in connection.capabilities:
            self._send_json(403, {
                "error": "hermes_unauthorized",
                "message": f"Hermes lacks required capability: {capability}"
            })
            return False
        return True

    def do_GET(self):
        # Hermes endpoints
        if self.path == '/hermes/status':
            connection = self._require_hermes_auth()
            if connection is None:
                return
            if not self._require_hermes_capability(connection, 'observe'):
                return
            try:
                status = hermes_adapter.read_status(connection)
                self._send_json(200, status)
            except PermissionError as e:
                self._send_json(403, {"error": "hermes_unauthorized", "message": str(e)})
            return

        elif self.path == '/hermes/events':
            connection = self._require_hermes_auth()
            if connection is None:
                return
            try:
                events = hermes_adapter.get_filtered_events(connection, limit=20)
                self._send_json(200, {
                    "events": [
                        {
                            "id": e.id,
                            "kind": e.kind,
                            "payload": e.payload,
                            "created_at": e.created_at
                        }
                        for e in events
                    ]
                })
            except Exception as e:
                self._send_json(500, {"error": "internal_error", "message": str(e)})
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
        if self.path == '/hermes/connect':
            authority_token = data.get('authority_token')
            if not authority_token:
                self._send_json(400, {"error": "missing_authority_token"})
                return
            try:
                connection = hermes_adapter.connect(authority_token)
                self._send_json(200, {
                    "hermes_id": connection.hermes_id,
                    "principal_id": connection.principal_id,
                    "capabilities": connection.capabilities,
                    "connected_at": connection.connected_at
                })
            except PermissionError as e:
                self._send_json(403, {"error": "hermes_unauthorized", "message": str(e)})
            except ValueError as e:
                self._send_json(401, {"error": "hermes_auth_expired", "message": str(e)})
            return

        elif self.path == '/hermes/pair':
            hermes_id = data.get('hermes_id')
            device_name = data.get('device_name', 'hermes-agent')
            if not hermes_id:
                self._send_json(400, {"error": "missing_hermes_id"})
                return
            try:
                pairing = hermes_adapter.pair_hermes(hermes_id, device_name)
                self._send_json(200, {
                    "hermes_id": pairing.hermes_id,
                    "capabilities": pairing.capabilities,
                    "principal_id": pairing.principal_id,
                    "paired_at": pairing.paired_at,
                    "authority_token": pairing.authority_token
                })
            except Exception as e:
                self._send_json(500, {"error": "pairing_failed", "message": str(e)})
            return

        elif self.path == '/hermes/summary':
            connection = self._require_hermes_auth()
            if connection is None:
                return
            if not self._require_hermes_capability(connection, 'summarize'):
                return
            
            summary_text = data.get('summary_text')
            authority_scope = data.get('authority_scope', 'observe')
            
            if not summary_text:
                self._send_json(400, {"error": "missing_summary_text"})
                return
            
            try:
                result = hermes_adapter.append_summary(connection, summary_text, authority_scope)
                self._send_json(200, result)
            except PermissionError as e:
                self._send_json(403, {"error": "hermes_unauthorized", "message": str(e)})
            except Exception as e:
                self._send_json(500, {"error": "internal_error", "message": str(e)})
            return

        # Check for Hermes attempting control commands (should be rejected)
        auth_header = self.headers.get('Authorization', '')
        if re.match(r'Hermes\s+', auth_header):
            if self.path in ['/miner/start', '/miner/stop', '/miner/set_mode']:
                self._send_json(403, {
                    "error": "hermes_unauthorized",
                    "message": "HERMES_UNAUTHORIZED: Hermes cannot issue control commands"
                })
                return

        # Standard miner control endpoints
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
