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
import re
import threading
import time
from datetime import datetime, timezone
from enum import Enum
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from typing import Dict, Optional


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

# Active Hermes connections (in-memory for session tracking)
# Maps hermes_id -> HermesConnection
active_hermes_connections: Dict[str, 'HermesConnection'] = {}


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
        # Hermes endpoints
        if self.path.startswith('/hermes/'):
            self._handle_hermes_get()
            return

        # Gateway endpoints
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

        # Hermes endpoints
        if self.path.startswith('/hermes/'):
            self._handle_hermes_post(data)
            return

        # Check for Hermes authorization on gateway control endpoints
        if self.path in ['/miner/start', '/miner/stop', '/miner/set_mode']:
            hermes_auth = self._get_hermes_auth()
            if hermes_auth:
                # Hermes is attempting control - reject it
                self._send_json(403, {
                    "error": "HERMES_UNAUTHORIZED",
                    "message": "Hermes agent does not have control capability",
                    "hermes_id": hermes_auth
                })
                return

        # Gateway control endpoints
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

    def _get_hermes_auth(self) -> Optional[str]:
        """Extract Hermes ID from Authorization header if present."""
        auth_header = self.headers.get('Authorization', '')
        if auth_header.startswith('Hermes '):
            return auth_header[7:]  # Extract hermes_id after 'Hermes '
        return None

    def _handle_hermes_get(self):
        """Handle Hermes GET endpoints."""
        # Lazy import to avoid circular dependency
        from hermes import connect, read_status, get_filtered_events, active_hermes_connections as conns

        path = self.path
        hermes_id = self._get_hermes_auth()

        if path == '/hermes/status':
            if not hermes_id:
                self._send_json(401, {"error": "missing_hermes_auth", "message": "Authorization: Hermes <hermes_id> required"})
                return

            # Find active connection
            connection = conns.get(hermes_id)
            if not connection:
                self._send_json(401, {"error": "not_connected", "message": "Hermes not connected. POST /hermes/connect first."})
                return

            try:
                status = read_status(connection)
                self._send_json(200, {
                    "connected": True,
                    "hermes_id": hermes_id,
                    "capabilities": connection.capabilities,
                    "status": status
                })
            except PermissionError as e:
                self._send_json(403, {"error": "HERMES_UNAUTHORIZED", "message": str(e)})

        elif path == '/hermes/events':
            if not hermes_id:
                self._send_json(401, {"error": "missing_hermes_auth", "message": "Authorization: Hermes <hermes_id> required"})
                return

            connection = conns.get(hermes_id)
            if not connection:
                self._send_json(401, {"error": "not_connected", "message": "Hermes not connected"})
                return

            # Parse limit from query params
            limit = 20
            if '?' in path:
                query = path.split('?', 1)[1]
                for param in query.split('&'):
                    if param.startswith('limit='):
                        try:
                            limit = int(param.split('=')[1])
                        except ValueError:
                            pass

            events = get_filtered_events(connection, limit=limit)
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

        else:
            self._send_json(404, {"error": "not_found", "path": path})

    def _handle_hermes_post(self, data: dict):
        """Handle Hermes POST endpoints."""
        # Lazy import to avoid circular dependency
        from hermes import connect, pair_hermes, append_summary, check_control_attempt, active_hermes_connections as conns

        path = self.path
        hermes_id = self._get_hermes_auth()

        if path == '/hermes/pair':
            # Create new Hermes pairing
            her_id = data.get('hermes_id')
            device_name = data.get('device_name', 'hermes-agent')

            if not her_id:
                self._send_json(400, {"error": "missing_hermes_id", "message": "hermes_id is required"})
                return

            pairing = pair_hermes(her_id, device_name)
            self._send_json(200, {
                "success": True,
                "hermes_id": pairing.hermes_id,
                "device_name": pairing.device_name,
                "capabilities": pairing.capabilities,
                "authority_token": pairing.token,
                "paired_at": pairing.paired_at,
                "token_expires_at": pairing.token_expires_at
            })

        elif path == '/hermes/connect':
            # Connect with authority token
            authority_token = data.get('authority_token')
            her_id = data.get('hermes_id')

            if not authority_token:
                self._send_json(400, {"error": "missing_token", "message": "authority_token is required"})
                return

            try:
                connection = connect(authority_token)

                # Check hermes_id matches if provided
                if her_id and connection.hermes_id != her_id:
                    self._send_json(401, {"error": "hermes_id_mismatch", "message": "hermes_id does not match token"})
                    return

                # Store active connection
                conns[connection.hermes_id] = connection

                self._send_json(200, {
                    "connected": True,
                    "hermes_id": connection.hermes_id,
                    "capabilities": connection.capabilities,
                    "connected_at": connection.connected_at,
                    "token_expires_at": connection.token_expires_at
                })
            except ValueError as e:
                self._send_json(401, {"error": "connection_failed", "message": str(e)})

        elif path == '/hermes/summary':
            # Append a summary
            if not hermes_id:
                self._send_json(401, {"error": "missing_hermes_auth", "message": "Authorization: Hermes <hermes_id> required"})
                return

            connection = conns.get(hermes_id)
            if not connection:
                self._send_json(401, {"error": "not_connected", "message": "Hermes not connected"})
                return

            summary_text = data.get('summary_text')
            authority_scope = data.get('authority_scope', 'observe')

            if not summary_text:
                self._send_json(400, {"error": "missing_summary_text", "message": "summary_text is required"})
                return

            try:
                event = append_summary(connection, summary_text, authority_scope)
                self._send_json(200, {
                    "appended": True,
                    "event_id": event.id,
                    "kind": event.kind,
                    "created_at": event.created_at
                })
            except PermissionError as e:
                self._send_json(403, {"error": "HERMES_UNAUTHORIZED", "message": str(e)})

        else:
            self._send_json(404, {"error": "not_found", "path": path})


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
