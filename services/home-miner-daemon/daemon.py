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

    def do_GET(self):
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

        # Hermes-specific endpoints
        if self.path == '/hermes/connect':
            self._handle_hermes_connect(data)
        elif self.path == '/hermes/pair':
            self._handle_hermes_pair(data)
        elif self.path == '/hermes/summary':
            self._handle_hermes_summary(data)
        elif self.path == '/miner/start':
            self._handle_control_check() or self._send_json(200 if miner.start()["success"] else 400, miner.start())
        elif self.path == '/miner/stop':
            self._handle_control_check() or self._send_json(200 if miner.stop()["success"] else 400, miner.stop())
        elif self.path == '/miner/set_mode':
            mode = data.get('mode')
            if not mode:
                self._send_json(400, {"error": "missing_mode"})
                return
            self._handle_control_check() or self._send_json(200 if miner.set_mode(mode)["success"] else 400, miner.set_mode(mode))
        else:
            self._send_json(404, {"error": "not_found"})

    def _handle_control_check(self) -> Optional[bool]:
        """Check if request is from Hermes and block control attempts. Returns True if blocked."""
        auth_header = self.headers.get('Authorization', '')
        if auth_header.startswith('Hermes '):
            hermes_id = auth_header[7:]  # Extract hermes_id after "Hermes "
            self._send_json(403, {
                "error": "HERMES_UNAUTHORIZED",
                "message": "Hermes agents cannot issue control commands"
            })
            return True
        return None

    def _handle_hermes_connect(self, data: dict):
        """Handle Hermes connection with authority token."""
        authority_token = data.get('authority_token')
        if not authority_token:
            self._send_json(400, {"error": "missing_authority_token"})
            return

        try:
            connection = hermes.connect(authority_token)
            self._send_json(200, {
                "connected": True,
                **connection.to_dict()
            })
        except ValueError as e:
            self._send_json(401, {"error": str(e)})

    def _handle_hermes_pair(self, data: dict):
        """Handle Hermes pairing request."""
        hermes_id = data.get('hermes_id')
        device_name = data.get('device_name')

        if not hermes_id:
            self._send_json(400, {"error": "missing_hermes_id"})
            return
        if not device_name:
            device_name = f"hermes-{hermes_id}"

        try:
            pairing = hermes.pair_hermes(hermes_id, device_name)
            # Generate authority token for the pairing
            token = hermes.generate_authority_token(
                hermes_id=pairing.hermes_id,
                principal_id=pairing.principal_id,
                capabilities=pairing.capabilities,
                expires_in_hours=24
            )
            self._send_json(200, {
                **pairing.to_dict(),
                "authority_token": token,
            })
        except Exception as e:
            self._send_json(500, {"error": str(e)})

    def _handle_hermes_summary(self, data: dict):
        """Handle Hermes summary append."""
        auth_header = self.headers.get('Authorization', '')
        if not auth_header.startswith('Hermes '):
            self._send_json(401, {"error": "missing_hermes_authorization"})
            return

        hermes_id = auth_header[7:]

        # Get or create connection from pairing
        pairing = hermes.get_pairing(hermes_id)
        if not pairing:
            self._send_json(401, {"error": "HERMES_UNAUTHORIZED: Unknown hermes_id"})
            return

        # Create temporary connection for authorization check
        connection = hermes.HermesConnection(
            hermes_id=pairing.hermes_id,
            principal_id=pairing.principal_id,
            capabilities=pairing.capabilities,
            connected_at=datetime.now(timezone.utc).isoformat(),
        )

        summary_text = data.get('summary_text')
        authority_scope = data.get('authority_scope', 'observe')

        if not summary_text:
            self._send_json(400, {"error": "missing_summary_text"})
            return

        try:
            result = hermes.append_summary(connection, summary_text, authority_scope)
            self._send_json(200, result)
        except PermissionError as e:
            self._send_json(403, {"error": str(e)})

    def do_GET(self):
        # Hermes-specific endpoints
        if self.path.startswith('/hermes/'):
            self._handle_hermes_get()
            return

        if self.path == '/health':
            self._send_json(200, miner.health)
        elif self.path == '/status':
            self._send_json(200, miner.get_snapshot())
        else:
            self._send_json(404, {"error": "not_found"})

    def _handle_hermes_get(self):
        """Handle Hermes GET endpoints."""
        auth_header = self.headers.get('Authorization', '')
        if not auth_header.startswith('Hermes '):
            self._send_json(401, {"error": "missing_hermes_authorization"})
            return

        hermes_id = auth_header[7:]

        # Get pairing
        pairing = hermes.get_pairing(hermes_id)
        if not pairing:
            self._send_json(401, {"error": "HERMES_UNAUTHORIZED: Unknown hermes_id"})
            return

        # Create connection for capability checks
        connection = hermes.HermesConnection(
            hermes_id=pairing.hermes_id,
            principal_id=pairing.principal_id,
            capabilities=pairing.capabilities,
            connected_at=datetime.now(timezone.utc).isoformat(),
        )

        if self.path == '/hermes/status':
            try:
                status = hermes.read_status(connection)
                self._send_json(200, status)
            except PermissionError as e:
                self._send_json(403, {"error": str(e)})
        elif self.path == '/hermes/events':
            # Parse limit from query params
            limit = 20
            if '?' in self.path:
                query = self.path.split('?')[1]
                for param in query.split('&'):
                    if param.startswith('limit='):
                        try:
                            limit = int(param.split('=')[1])
                        except ValueError:
                            pass

            events = hermes.get_filtered_events(connection, limit=limit)
            self._send_json(200, {"events": events})
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
