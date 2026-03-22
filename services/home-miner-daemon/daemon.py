#!/usr/bin/env python3
"""
Zend Home Miner Daemon

LAN-only control service for milestone 1.
Binds to 127.0.0.1 only for local development/testing.
Production deployment uses the local network interface.

This is a milestone 1 simulator that exposes the same contract
a real miner backend will use.

Hermes Adapter Endpoints:
- POST /hermes/connect    — Validate authority token and establish connection
- POST /hermes/pair       — Create Hermes pairing record
- GET  /hermes/status     — Read miner status through adapter
- POST /hermes/summary    — Append summary to event spine
- GET  /hermes/events     — Read filtered events (no user_message)
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

# Import Hermes adapter
from hermes import (
    HermesConnection,
    HermesUnauthorizedError,
    HermesInvalidTokenError,
    HermesError,
    connect as hermes_connect,
    pair_hermes as hermes_pair,
    read_status as hermes_read_status,
    append_summary as hermes_append_summary,
    get_filtered_events as hermes_get_filtered_events,
    get_connection,
    HERMES_CAPABILITIES,
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

    def log_message(self, format, *args):
        """Suppress default logging."""
        pass

    def _send_json(self, status: int, data: dict):
        self.send_response(status)
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps(data).encode())

    def _get_hermes_id_from_auth(self) -> Optional[str]:
        """Extract hermes_id from Authorization header."""
        auth_header = self.headers.get('Authorization', '')
        match = re.match(r'Hermes\s+(\S+)', auth_header)
        if match:
            return match.group(1)
        return None

    def _send_hermes_error(self, error: HermesError):
        """Send Hermes-specific error response."""
        if isinstance(error, HermesUnauthorizedError):
            self._send_json(403, {"error": error.error_code, "message": error.message})
        elif isinstance(error, HermesInvalidTokenError):
            self._send_json(401, {"error": error.error_code, "message": error.message})
        else:
            self._send_json(400, {"error": error.error_code, "message": error.message})

    def do_GET(self):
        # Hermes endpoints
        hermes_id = self._get_hermes_id_from_auth()
        
        if hermes_id:
            if self.path == '/hermes/status':
                try:
                    connection = get_connection(hermes_id)
                    if not connection:
                        self._send_json(403, {
                            "error": "HERMES_UNAUTHORIZED",
                            "message": "No active session. Use /hermes/connect first."
                        })
                        return
                    status = hermes_read_status(connection)
                    self._send_json(200, status)
                except HermesError as e:
                    self._send_hermes_error(e)
                return
                
            elif self.path == '/hermes/events':
                try:
                    connection = get_connection(hermes_id)
                    if not connection:
                        self._send_json(403, {
                            "error": "HERMES_UNAUTHORIZED",
                            "message": "No active session. Use /hermes/connect first."
                        })
                        return
                    events = hermes_get_filtered_events(connection, limit=20)
                    self._send_json(200, {"events": events})
                except HermesError as e:
                    self._send_hermes_error(e)
                return
        
        # Standard endpoints
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

        # Hermes endpoints (no auth required for connect/pair, auth required for summary)
        if self.path == '/hermes/connect':
            authority_token = data.get('authority_token')
            if not authority_token:
                self._send_json(400, {"error": "missing_authority_token"})
                return
            try:
                connection = hermes_connect(authority_token)
                self._send_json(200, {
                    "hermes_id": connection.hermes_id,
                    "principal_id": connection.principal_id,
                    "capabilities": connection.capabilities,
                    "connected_at": connection.connected_at,
                    "authority_scope": connection.authority_scope
                })
            except HermesError as e:
                self._send_hermes_error(e)
            return

        elif self.path == '/hermes/pair':
            hermes_id = data.get('hermes_id')
            device_name = data.get('device_name')
            if not hermes_id:
                self._send_json(400, {"error": "missing_hermes_id"})
                return
            if not device_name:
                device_name = f"hermes-{hermes_id}"
            
            try:
                pairing = hermes_pair(hermes_id, device_name)
                self._send_json(200, {
                    "hermes_id": pairing.hermes_id,
                    "capabilities": pairing.capabilities,
                    "paired_at": pairing.paired_at,
                    "token": pairing.token
                })
            except HermesError as e:
                self._send_hermes_error(e)
            return

        elif self.path == '/hermes/summary':
            hermes_id = self._get_hermes_id_from_auth()
            if not hermes_id:
                self._send_json(401, {"error": "HERMES_UNAUTHORIZED", "message": "Missing Hermes auth"})
                return
            
            try:
                connection = get_connection(hermes_id)
                if not connection:
                    self._send_json(403, {"error": "HERMES_UNAUTHORIZED", "message": "No active session"})
                    return
                
                summary_text = data.get('summary_text')
                authority_scope = data.get('authority_scope', 'observe')
                
                if not summary_text:
                    self._send_json(400, {"error": "missing_summary_text"})
                    return
                
                result = hermes_append_summary(connection, summary_text, authority_scope)
                self._send_json(200, result)
            except HermesError as e:
                self._send_hermes_error(e)
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
