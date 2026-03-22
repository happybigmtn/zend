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
import sys
import json
import os
import threading
import time
from datetime import datetime, timezone
from enum import Enum
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from typing import Optional

# Add current directory to path for imports
_daemon_dir = Path(__file__).resolve().parent
if str(_daemon_dir) not in sys.path:
    sys.path.insert(0, str(_daemon_dir))

# Import Hermes adapter
from hermes import (
    HERMES_CAPABILITIES,
    HermesConnection,
    connect,
    reconnect_with_token,
    pair_hermes,
    read_status as hermes_read_status,
    append_summary,
    get_filtered_events,
    get_hermes_connection_info,
    validate_authority_token,
)


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

    # Hermes connection state (thread-safe via daemon lock)
    hermes_connections: dict = {}

    def log_message(self, format, *args):
        """Suppress default logging."""
        pass

    def _send_json(self, status: int, data: dict):
        self.send_response(status)
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps(data).encode())

    def _get_hermes_auth(self) -> tuple[Optional[str], Optional[str]]:
        """
        Extract Hermes auth from request headers.
        
        Returns:
            Tuple of (hermes_id, token_data) or (None, None) if not authenticated
        """
        auth_header = self.headers.get('Authorization', '')
        
        if not auth_header.startswith('Hermes '):
            return None, None
        
        hermes_id = auth_header[7:]  # Strip 'Hermes ' prefix
        
        # Try to get stored token for this Hermes
        try:
            connection = reconnect_with_token(hermes_id)
            self.hermes_connections[hermes_id] = connection
            return hermes_id, connection
        except ValueError:
            return hermes_id, None

    def do_GET(self):
        # Health endpoint (no auth required)
        if self.path == '/health':
            self._send_json(200, miner.health)
            return
        
        # Status endpoint (no auth required for milestone 1)
        if self.path == '/status':
            self._send_json(200, miner.get_snapshot())
            return
        
        # Hermes endpoints
        hermes_id, connection = self._get_hermes_auth()
        
        if hermes_id is None:
            self._send_json(401, {"error": "unauthorized", "message": "Hermes authorization required"})
            return
        
        if connection is None:
            self._send_json(401, {"error": "hermes_not_paired", "message": f"Hermes '{hermes_id}' is not paired"})
            return
        
        # Hermes GET endpoints
        if self.path == '/hermes/status':
            try:
                status = hermes_read_status(connection)
                self._send_json(200, status)
            except PermissionError as e:
                self._send_json(403, {"error": "hermes_unauthorized", "message": str(e)})
            return
        
        if self.path == '/hermes/events':
            # Get filtered events (blocks user_message)
            events = get_filtered_events(connection, limit=20)
            self._send_json(200, {"events": events})
            return
        
        if self.path == '/hermes/info':
            # Get connection info
            info = get_hermes_connection_info(connection)
            self._send_json(200, info)
            return
        
        self._send_json(404, {"error": "not_found"})

    def do_POST(self):
        content_length = int(self.headers.get('Content-Length', 0))
        body = self.rfile.read(content_length)

        try:
            data = json.loads(body) if body else {}
        except json.JSONDecodeError:
            self._send_json(400, {"error": "invalid_json"})
            return

        # Control endpoints (no Hermes auth - these require device auth)
        if self.path == '/miner/start':
            # Check if this is a Hermes attempting control (should be blocked)
            hermes_id, connection = self._get_hermes_auth()
            if hermes_id is not None:
                self._send_json(403, {
                    "error": "hermes_unauthorized",
                    "code": "HERMES_UNAUTHORIZED",
                    "message": "Hermes cannot issue control commands"
                })
                return
            
            result = miner.start()
            self._send_json(200 if result["success"] else 400, result)
            return
        
        if self.path == '/miner/stop':
            # Check if this is a Hermes attempting control (should be blocked)
            hermes_id, connection = self._get_hermes_auth()
            if hermes_id is not None:
                self._send_json(403, {
                    "error": "hermes_unauthorized",
                    "code": "HERMES_UNAUTHORIZED",
                    "message": "Hermes cannot issue control commands"
                })
                return
            
            result = miner.stop()
            self._send_json(200 if result["success"] else 400, result)
            return
        
        if self.path == '/miner/set_mode':
            # Check if this is a Hermes attempting control (should be blocked)
            hermes_id, connection = self._get_hermes_auth()
            if hermes_id is not None:
                self._send_json(403, {
                    "error": "hermes_unauthorized",
                    "code": "HERMES_UNAUTHORIZED",
                    "message": "Hermes cannot issue control commands"
                })
                return
            
            mode = data.get('mode')
            if not mode:
                self._send_json(400, {"error": "missing_mode"})
                return
            result = miner.set_mode(mode)
            self._send_json(200 if result["success"] else 400, result)
            return
        
        # Hermes POST endpoints
        if self.path == '/hermes/connect':
            # Connect with authority token
            token_data = data.get('authority_token', {})
            try:
                connection = connect(token_data)
                self.hermes_connections[connection.hermes_id] = connection
                self._send_json(200, {
                    "connected": True,
                    "hermes_id": connection.hermes_id,
                    "principal_id": connection.principal_id,
                    "capabilities": connection.capabilities,
                    "connected_at": connection.connected_at
                })
            except ValueError as e:
                self._send_json(401, {"error": "hermes_connect_failed", "message": str(e)})
            return
        
        if self.path == '/hermes/pair':
            # Pair a new Hermes
            hermes_id = data.get('hermes_id')
            device_name = data.get('device_name', f"hermes-{hermes_id}")
            
            if not hermes_id:
                self._send_json(400, {"error": "missing_hermes_id"})
                return
            
            # Get or create principal
            try:
                from store import load_or_create_principal
                principal = load_or_create_principal()
            except ImportError:
                principal_id = "00000000-0000-0000-0000-000000000000"
            else:
                principal_id = principal.id
            
            pairing = pair_hermes(hermes_id, device_name, principal_id)
            
            self._send_json(200, {
                "paired": True,
                "hermes_id": pairing.hermes_id,
                "device_name": pairing.device_name,
                "principal_id": pairing.principal_id,
                "capabilities": pairing.capabilities,
                "paired_at": pairing.paired_at,
                "token_expires_at": pairing.token_expires_at
            })
            return
        
        if self.path == '/hermes/summary':
            # Append a summary (requires Hermes auth)
            hermes_id, connection = self._get_hermes_auth()
            
            if hermes_id is None:
                self._send_json(401, {"error": "unauthorized", "message": "Hermes authorization required"})
                return
            
            if connection is None:
                self._send_json(401, {"error": "hermes_not_paired", "message": f"Hermes '{hermes_id}' is not paired"})
                return
            
            summary_text = data.get('summary_text', '')
            authority_scope = data.get('authority_scope', 'observe')
            
            if not summary_text:
                self._send_json(400, {"error": "missing_summary_text"})
                return
            
            try:
                result = append_summary(connection, summary_text, authority_scope)
                if result.get('appended'):
                    self._send_json(200, result)
                else:
                    self._send_json(500, result)
            except PermissionError as e:
                self._send_json(403, {"error": "hermes_unauthorized", "message": str(e)})
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
