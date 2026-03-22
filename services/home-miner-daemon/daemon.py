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

# Import Hermes adapter
from hermes import (
    HermesConnection,
    HermesUnauthorizedError,
    HermesTokenExpiredError,
    HermesInvalidTokenError,
    connect as hermes_connect,
    pair_hermes,
    read_status as hermes_read_status,
    append_summary as hermes_append_summary,
    get_filtered_events,
    is_hermes_auth_header,
    extract_hermes_id,
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

    def _is_hermes_request(self) -> bool:
        """Check if this request has Hermes auth header."""
        auth = self.headers.get('Authorization', '')
        return is_hermes_auth_header(auth)

    def _get_hermes_connection(self) -> HermesConnection:
        """Extract and validate Hermes connection from request."""
        auth = self.headers.get('Authorization', '')
        hermes_id = extract_hermes_id(auth)
        if not hermes_id:
            raise HermesUnauthorizedError("Invalid Hermes authorization header")
        
        # For Hermes auth, the token is the hermes_id (simplified for milestone 1)
        # In production, this would be a proper JWT or similar
        try:
            return hermes_connect(json.dumps({
                "hermes_id": hermes_id,
                "principal_id": "principal-auto",
                "capabilities": ["observe", "summarize"],
                "expires_at": "2030-01-01T00:00:00Z"
            }))
        except (HermesInvalidTokenError, HermesTokenExpiredError) as e:
            raise HermesUnauthorizedError(str(e))

    def do_GET(self):
        # Hermes-specific endpoints
        if self._is_hermes_request():
            if self.path == '/hermes/status':
                self._handle_hermes_status()
                return
            elif self.path == '/hermes/events':
                self._handle_hermes_events()
                return
            elif self.path.startswith('/miner/') or self.path == '/status':
                # Block Hermes from reading miner status via gateway endpoint
                self._send_json(403, {
                    "error": "HERMES_UNAUTHORIZED",
                    "message": "Use /hermes/status for Hermes reads"
                })
                return
        
        # Regular endpoints
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

        # Hermes-specific endpoints (some don't require auth header)
        # /hermes/pair is special - it's used to create a pairing
        if self.path == '/hermes/pair':
            self._handle_hermes_pair(data)
            return
        elif self.path == '/hermes/connect':
            self._handle_hermes_connect(data)
            return

        # For other Hermes endpoints, require auth header
        if self._is_hermes_request():
            if self.path == '/hermes/summary':
                self._handle_hermes_summary(data)
                return
            elif self.path.startswith('/miner/'):
                # Block all control commands from Hermes
                self._send_json(403, {
                    "error": "HERMES_UNAUTHORIZED",
                    "message": "Hermes cannot issue control commands"
                })
                return

        # Regular endpoints (block if Hermes tries to use regular auth)
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

    def _handle_hermes_connect(self, data: dict):
        """Handle POST /hermes/connect - establish Hermes connection."""
        token = data.get('authority_token')
        if not token:
            self._send_json(400, {"error": "missing_authority_token"})
            return
        
        try:
            connection = hermes_connect(token)
            self._send_json(200, {
                "connected": True,
                "hermes_id": connection.hermes_id,
                "capabilities": connection.capabilities,
                "connected_at": connection.connected_at,
            })
        except HermesInvalidTokenError as e:
            self._send_json(401, {"error": "invalid_token", "message": str(e)})
        except HermesTokenExpiredError as e:
            self._send_json(401, {"error": "token_expired", "message": str(e)})
        except HermesUnauthorizedError as e:
            self._send_json(403, {"error": "unauthorized", "message": str(e)})

    def _handle_hermes_pair(self, data: dict):
        """Handle POST /hermes/pair - create Hermes pairing."""
        hermes_id = data.get('hermes_id')
        device_name = data.get('device_name', f"hermes-{hermes_id}")
        
        if not hermes_id:
            self._send_json(400, {"error": "missing_hermes_id"})
            return
        
        pairing = pair_hermes(hermes_id, device_name)
        self._send_json(200, {
            "hermes_id": pairing.hermes_id,
            "capabilities": pairing.capabilities,
            "paired_at": pairing.paired_at,
        })

    def _handle_hermes_status(self):
        """Handle GET /hermes/status - read miner status via adapter."""
        try:
            connection = self._get_hermes_connection()
            status = hermes_read_status(connection)
            self._send_json(200, {
                "hermes_id": connection.hermes_id,
                "status": status,
            })
        except HermesUnauthorizedError as e:
            self._send_json(403, {"error": "unauthorized", "message": str(e)})

    def _handle_hermes_summary(self, data: dict):
        """Handle POST /hermes/summary - append Hermes summary."""
        summary_text = data.get('summary_text')
        authority_scope = data.get('authority_scope', 'observe')
        
        if not summary_text:
            self._send_json(400, {"error": "missing_summary_text"})
            return
        
        try:
            connection = self._get_hermes_connection()
            event = hermes_append_summary(connection, summary_text, authority_scope)
            self._send_json(200, {
                "appended": True,
                "event_id": event.id,
                "created_at": event.created_at,
            })
        except HermesUnauthorizedError as e:
            self._send_json(403, {"error": "unauthorized", "message": str(e)})

    def _handle_hermes_events(self):
        """Handle GET /hermes/events - read filtered events."""
        try:
            connection = self._get_hermes_connection()
            
            # Parse limit from query params
            limit = 20
            if '?' in self.path:
                query = self.path.split('?', 1)[1]
                for param in query.split('&'):
                    if param.startswith('limit='):
                        try:
                            limit = int(param.split('=')[1])
                        except ValueError:
                            pass
            
            events = get_filtered_events(connection, limit)
            self._send_json(200, {
                "hermes_id": connection.hermes_id,
                "events": [
                    {
                        "id": e.id,
                        "kind": e.kind,
                        "payload": e.payload,
                        "created_at": e.created_at,
                    }
                    for e in events
                ],
            })
        except HermesUnauthorizedError as e:
            self._send_json(403, {"error": "unauthorized", "message": str(e)})


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
