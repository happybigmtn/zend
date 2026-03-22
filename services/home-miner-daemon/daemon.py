#!/usr/bin/env python3
"""
Zend Home Miner Daemon

LAN-only control service for milestone 1.
Binds to 127.0.0.1 only for local development/testing.
Production deployment uses the local network interface.

This is a milestone 1 simulator that exposes the same contract
a real miner backend will use.

Hermes Adapter Integration:
- Hermes can connect with observe and summarize capabilities only
- Hermes CANNOT issue control commands (returns 403)
- Hermes cannot read user_message events (filtered)
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
from functools import wraps


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


def require_hermes_auth(f):
    """Decorator to require Hermes authentication."""
    @wraps(f)
    def wrapped(self, *args, **kwargs):
        auth_header = self.headers.get('Authorization', '')
        
        # Parse Hermes auth: "Hermes <hermes_id>"
        if not auth_header.startswith('Hermes '):
            return self._send_json(401, {
                "error": "unauthorized",
                "message": "Hermes authorization required"
            })
        
        hermes_id = auth_header[7:].strip()
        
        try:
            from . import hermes as hermes_adapter
            connection = hermes_adapter.validate_hermes_auth(hermes_id)
            return f(self, connection, *args, **kwargs)
        except ValueError as e:
            return self._send_json(401, {
                "error": "unauthorized",
                "message": str(e)
            })
    return wrapped


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

    def _parse_body(self):
        """Parse JSON body from request."""
        content_length = int(self.headers.get('Content-Length', 0))
        body = self.rfile.read(content_length)
        if not body:
            return {}
        try:
            return json.loads(body)
        except json.JSONDecodeError:
            self._send_json(400, {"error": "invalid_json"})
            return None

    def do_GET(self):
        # Hermes endpoints
        if self.path == '/hermes/status':
            self._handle_hermes_status()
        elif self.path == '/hermes/events':
            self._handle_hermes_events()
        # Standard endpoints
        elif self.path == '/health':
            self._send_json(200, miner.health)
        elif self.path == '/status':
            self._send_json(200, miner.get_snapshot())
        else:
            self._send_json(404, {"error": "not_found"})

    def do_POST(self):
        data = self._parse_body()
        if data is None:
            return

        # Hermes endpoints
        if self.path == '/hermes/connect':
            self._handle_hermes_connect(data)
        elif self.path == '/hermes/pair':
            self._handle_hermes_pair(data)
        elif self.path == '/hermes/summary':
            self._handle_hermes_summary(data)
        # Standard endpoints
        elif self.path == '/miner/start':
            self._handle_control_attempt()
        elif self.path == '/miner/stop':
            self._handle_control_attempt()
        elif self.path == '/miner/set_mode':
            self._handle_control_attempt()
        else:
            self._send_json(404, {"error": "not_found"})

    def _handle_control_attempt(self):
        """Block control commands from Hermes (non-Hermes clients get through)."""
        auth_header = self.headers.get('Authorization', '')
        
        # If Hermes is attempting control, block it
        if auth_header.startswith('Hermes '):
            self._send_json(403, {
                "error": "hermes_unauthorized",
                "message": "HERMES_UNAUTHORIZED: control commands are not permitted for Hermes agents"
            })
            return
        
        # Non-Hermes clients proceed with normal control
        data = self._parse_body()
        if data is None:
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

    def _handle_hermes_pair(self, data: dict):
        """Pair a new Hermes agent."""
        from . import hermes as hermes_adapter
        
        hermes_id = data.get('hermes_id')
        device_name = data.get('device_name', 'hermes-agent')
        
        if not hermes_id:
            self._send_json(400, {"error": "missing_hermes_id"})
            return
        
        try:
            pairing = hermes_adapter.pair_hermes(hermes_id, device_name)
            self._send_json(200, {
                "success": True,
                "hermes_id": pairing.hermes_id,
                "device_name": pairing.device_name,
                "capabilities": pairing.capabilities,
                "token": pairing.token,
                "paired_at": pairing.paired_at,
                "token_expires_at": pairing.token_expires_at
            })
        except Exception as e:
            self._send_json(500, {"error": str(e)})

    def _handle_hermes_connect(self, data: dict):
        """Connect with authority token."""
        from . import hermes as hermes_adapter
        
        authority_token = data.get('authority_token')
        if not authority_token:
            self._send_json(400, {"error": "missing_authority_token"})
            return
        
        try:
            connection = hermes_adapter.connect(authority_token)
            self._send_json(200, {
                "connected": True,
                "hermes_id": connection.hermes_id,
                "principal_id": connection.principal_id,
                "capabilities": connection.capabilities,
                "connected_at": connection.connected_at
            })
        except ValueError as e:
            self._send_json(401, {"error": str(e)})

    @require_hermes_auth
    def _handle_hermes_status(self, connection):
        """Read miner status through Hermes adapter."""
        from . import hermes as hermes_adapter
        
        try:
            status = hermes_adapter.read_status(connection)
            self._send_json(200, {
                "hermes_id": connection.hermes_id,
                "status": status
            })
        except PermissionError as e:
            self._send_json(403, {"error": str(e)})

    @require_hermes_auth
    def _handle_hermes_summary(self, connection, data: dict):
        """Append a Hermes summary to the event spine."""
        from . import hermes as hermes_adapter
        
        summary_text = data.get('summary_text')
        authority_scope = data.get('authority_scope', 'observe')
        
        if not summary_text:
            self._send_json(400, {"error": "missing_summary_text"})
            return
        
        try:
            result = hermes_adapter.append_summary(
                connection,
                summary_text,
                authority_scope
            )
            self._send_json(200, result)
        except PermissionError as e:
            self._send_json(403, {"error": str(e)})

    @require_hermes_auth
    def _handle_hermes_events(self, connection):
        """Read filtered events (no user_message for Hermes)."""
        from . import hermes as hermes_adapter
        
        try:
            events = hermes_adapter.get_filtered_events(connection, limit=20)
            self._send_json(200, {
                "hermes_id": connection.hermes_id,
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
            self._send_json(500, {"error": str(e)})


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
