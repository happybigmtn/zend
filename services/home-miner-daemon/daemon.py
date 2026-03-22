#!/usr/bin/env python3
"""
Zend Home Miner Daemon

LAN-only control service for milestone 1.
Binds to 127.0.0.1 only for local development/testing.
Production deployment uses the local network interface.

This is a milestone 1 simulator that exposes the same contract
a real miner backend will use.

Hermes Adapter Integration:
- POST /hermes/pair - Create Hermes pairing with observe+summarize capabilities
- GET /hermes/token/<hermes_id> - Generate authority token for pairing
- POST /hermes/connect - Connect with authority token, returns connection state
- GET /hermes/status - Read miner status through adapter (requires Hermes auth)
- POST /hermes/summary - Append summary to event spine (requires Hermes auth)
- GET /hermes/events - Read filtered events, no user_message (requires Hermes auth)
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
from typing import Optional, Tuple


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

# Hermes connection cache (in-memory for the daemon lifetime)
_hermes_connections: dict[str, 'HermesConnection'] = {}


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

    def _get_hermes_auth(self) -> Tuple[Optional[str], Optional[str]]:
        """
        Extract Hermes auth from Authorization header.
        
        Expected format: "Authorization: Hermes <hermes_id>"
        Returns (hermes_id, error_message).
        """
        auth_header = self.headers.get('Authorization', '')
        
        if not auth_header:
            return None, "HERMES_UNAUTHORIZED: Authorization header required"
        
        # Parse "Hermes <hermes_id>" format
        match = re.match(r'^Hermes\s+(.+)$', auth_header, re.IGNORECASE)
        if not match:
            return None, "HERMES_UNAUTHORIZED: Invalid Authorization format. Use 'Hermes <hermes_id>'"
        
        hermes_id = match.group(1)
        
        # Check if connected
        if hermes_id not in _hermes_connections:
            return None, "HERMES_UNAUTHORIZED: Not connected. Call /hermes/connect first"
        
        return hermes_id, None

    def _require_hermes_auth(self):
        """Require Hermes authentication. Returns connection or sends 403."""
        hermes_id, error = self._get_hermes_auth()
        if error:
            self._send_json(403, {"error": error})
            return None
        return _hermes_connections[hermes_id]

    def do_GET(self):
        # Hermes routes
        if self.path.startswith('/hermes/'):
            self._handle_hermes_get()
            return
        
        # Standard routes
        if self.path == '/health':
            self._send_json(200, miner.health)
        elif self.path == '/status':
            self._send_json(200, miner.get_snapshot())
        else:
            self._send_json(404, {"error": "not_found"})

    def do_POST(self):
        # Hermes routes
        if self.path.startswith('/hermes/'):
            self._handle_hermes_post()
            return
        
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

    def _handle_hermes_get(self):
        """Handle Hermes GET routes."""
        import hermes
        
        # GET /hermes/status - Read miner status
        if self.path == '/hermes/status':
            connection = self._require_hermes_auth()
            if connection is None:
                return
            try:
                status = hermes.read_status(connection)
                self._send_json(200, status)
            except PermissionError as e:
                self._send_json(403, {"error": str(e)})
            return
        
        # GET /hermes/events - Read filtered events
        if self.path == '/hermes/events':
            connection = self._require_hermes_auth()
            if connection is None:
                return
            events = hermes.get_filtered_events(connection)
            self._send_json(200, {"events": events})
            return
        
        # GET /hermes/token/<hermes_id> - Generate authority token
        token_match = re.match(r'^/hermes/token/(.+)$', self.path)
        if token_match:
            hermes_id = token_match.group(1)
            try:
                token = hermes.generate_authority_token(hermes_id)
                self._send_json(200, {
                    "hermes_id": hermes_id,
                    "authority_token": token
                })
            except ValueError as e:
                self._send_json(404, {"error": str(e)})
            return
        
        # GET /hermes/pairing/<hermes_id> - Get pairing status
        pairing_match = re.match(r'^/hermes/pairing/(.+)$', self.path)
        if pairing_match:
            hermes_id = pairing_match.group(1)
            pairing = hermes.get_hermes_pairing(hermes_id)
            if pairing:
                self._send_json(200, {
                    "hermes_id": pairing.hermes_id,
                    "device_name": pairing.device_name,
                    "capabilities": pairing.capabilities,
                    "paired_at": pairing.paired_at,
                    "is_valid": not hermes._is_token_expired(pairing.token_expires_at)
                })
            else:
                self._send_json(404, {"error": f"HERMES_NOT_PAIRED: '{hermes_id}' not paired"})
            return
        
        self._send_json(404, {"error": "not_found"})

    def _handle_hermes_post(self):
        """Handle Hermes POST routes."""
        import hermes
        
        content_length = int(self.headers.get('Content-Length', 0))
        body = self.rfile.read(content_length)

        try:
            data = json.loads(body) if body else {}
        except json.JSONDecodeError:
            self._send_json(400, {"error": "invalid_json"})
            return
        
        # POST /hermes/pair - Create Hermes pairing
        if self.path == '/hermes/pair':
            hermes_id = data.get('hermes_id')
            device_name = data.get('device_name')
            
            if not hermes_id:
                self._send_json(400, {"error": "hermes_id is required"})
                return
            
            try:
                pairing = hermes.pair_hermes(hermes_id, device_name)
                self._send_json(200, {
                    "hermes_id": pairing.hermes_id,
                    "device_name": pairing.device_name,
                    "capabilities": pairing.capabilities,
                    "paired_at": pairing.paired_at,
                    "token_expires_at": pairing.token_expires_at
                })
            except ValueError as e:
                self._send_json(400, {"error": str(e)})
            return
        
        # POST /hermes/connect - Connect with authority token
        if self.path == '/hermes/connect':
            authority_token = data.get('authority_token')
            
            if not authority_token:
                self._send_json(400, {"error": "authority_token is required"})
                return
            
            try:
                connection = hermes.connect(authority_token)
                _hermes_connections[connection.hermes_id] = connection
                self._send_json(200, {
                    "connected": True,
                    "hermes_id": connection.hermes_id,
                    "principal_id": connection.principal_id,
                    "capabilities": connection.capabilities,
                    "connected_at": connection.connected_at,
                    "token_expires_at": connection.token_expires_at
                })
            except ValueError as e:
                self._send_json(401, {"error": str(e)})
            return
        
        # POST /hermes/summary - Append summary to spine
        if self.path == '/hermes/summary':
            connection = self._require_hermes_auth()
            if connection is None:
                return
            
            summary_text = data.get('summary_text')
            authority_scope = data.get('authority_scope', 'observe')
            
            if not summary_text:
                self._send_json(400, {"error": "summary_text is required"})
                return
            
            try:
                result = hermes.append_summary(connection, summary_text, authority_scope)
                self._send_json(200, result)
            except PermissionError as e:
                self._send_json(403, {"error": str(e)})
            return
        
        # POST /hermes/disconnect - Disconnect Hermes
        if self.path == '/hermes/disconnect':
            hermes_id, error = self._get_hermes_auth()
            if error:
                self._send_json(403, {"error": error})
                return
            
            if hermes_id in _hermes_connections:
                del _hermes_connections[hermes_id]
            
            self._send_json(200, {"disconnected": True, "hermes_id": hermes_id})
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
