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

# Import Hermes adapter
from hermes import (
    HermesConnection,
    HermesPairing,
    connect as hermes_connect,
    read_status as hermes_read_status,
    append_summary as hermes_append_summary,
    get_filtered_events as hermes_get_filtered_events,
    pair_hermes,
    generate_hermes_token,
    get_hermes_status,
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

# Active Hermes connections (in-memory for milestone 1)
# In production, this would use a session store
active_hermes_connections: Dict[str, HermesConnection] = {}


def _extract_hermes_auth(headers) -> Optional[str]:
    """Extract Hermes authority token from request headers."""
    auth = headers.get('Authorization', '')
    if auth.startswith('Hermes '):
        return auth[7:]  # Remove 'Hermes ' prefix
    return None


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

    def _check_hermes_auth(self) -> Optional[HermesConnection]:
        """Check Hermes authorization and return connection if valid."""
        token = _extract_hermes_auth(self.headers)
        if not token:
            return None

        try:
            connection = hermes_connect(token)
            return connection
        except (ValueError, PermissionError):
            return None

    def do_GET(self):
        # Hermes endpoints
        if self.path == '/hermes/status':
            connection = self._check_hermes_auth()
            if not connection:
                self._send_json(401, {
                    "error": "HERMES_UNAUTHORIZED",
                    "message": "Valid Hermes authorization required"
                })
                return

            try:
                status = hermes_read_status(connection)
                self._send_json(200, status)
            except PermissionError as e:
                self._send_json(403, {"error": str(e)})
            return

        elif self.path == '/hermes/events':
            connection = self._check_hermes_auth()
            if not connection:
                self._send_json(401, {
                    "error": "HERMES_UNAUTHORIZED",
                    "message": "Valid Hermes authorization required"
                })
                return

            events = hermes_get_filtered_events(connection, limit=20)
            self._send_json(200, {
                "events": [
                    {
                        "id": e.id,
                        "kind": e.kind,
                        "principal_id": e.principal_id,
                        "payload": e.payload,
                        "created_at": e.created_at
                    }
                    for e in events
                ]
            })
            return

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
            # Connect with authority token
            token = data.get('authority_token')
            if not token:
                self._send_json(400, {"error": "missing_authority_token"})
                return

            try:
                connection = hermes_connect(token)
                active_hermes_connections[connection.hermes_id] = connection
                self._send_json(200, connection.to_dict())
            except ValueError as e:
                self._send_json(401, {"error": str(e)})
            except PermissionError as e:
                self._send_json(403, {"error": str(e)})
            return

        elif self.path == '/hermes/pair':
            # Pair Hermes agent
            hermes_id = data.get('hermes_id')
            device_name = data.get('device_name', 'hermes-agent')

            if not hermes_id:
                self._send_json(400, {"error": "missing_hermes_id"})
                return

            pairing = pair_hermes(hermes_id, device_name)
            token, expires = generate_hermes_token(hermes_id)

            self._send_json(200, {
                "hermes_id": pairing.hermes_id,
                "device_name": pairing.device_name,
                "capabilities": pairing.capabilities,
                "paired_at": pairing.paired_at,
                "token_expires_at": expires,
                "authority_token": token
            })
            return

        elif self.path == '/hermes/summary':
            # Append Hermes summary
            connection = self._check_hermes_auth()
            if not connection:
                self._send_json(401, {
                    "error": "HERMES_UNAUTHORIZED",
                    "message": "Valid Hermes authorization required"
                })
                return

            summary_text = data.get('summary_text')
            authority_scope = data.get('authority_scope', 'observe')

            if not summary_text:
                self._send_json(400, {"error": "missing_summary_text"})
                return

            try:
                event = hermes_append_summary(connection, summary_text, authority_scope)
                self._send_json(200, {
                    "appended": True,
                    "event_id": event.id,
                    "created_at": event.created_at
                })
            except PermissionError as e:
                self._send_json(403, {"error": str(e)})
            except ValueError as e:
                self._send_json(400, {"error": str(e)})
            return

        # Gateway control endpoints (reject Hermes authorization)
        elif self.path in ['/miner/start', '/miner/stop', '/miner/set_mode']:
            if _extract_hermes_auth(self.headers):
                self._send_json(403, {
                    "error": "HERMES_UNAUTHORIZED",
                    "message": "Hermes cannot issue control commands"
                })
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


class ThreadedHTTPServer(socketserver.ThreadingMixIn, HTTPServer):
    """Threaded HTTP server for handling concurrent requests."""
    allow_reuse_address = True


def run_server(host: str = BIND_HOST, port: int = BIND_PORT):
    """Run the gateway server."""
    server = ThreadedHTTPServer((host, port), GatewayHandler)
    print(f"Zend Home Miner Daemon starting on {host}:{port}")
    print(f"LISTENING ON: {host}:{port}")
    print("Hermes adapter: enabled")
    print("Press Ctrl+C to stop")

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down...")
        server.shutdown()


if __name__ == '__main__':
    run_server()
