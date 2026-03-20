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
from dataclasses import asdict
from typing import Optional

# Handle relative imports when running as script vs as module
try:
    from .adapter import (
        HermesAdapter,
        HermesAdapterError,
        InvalidTokenError,
        ExpiredTokenError,
        UnauthorizedError,
    )
except ImportError:
    from adapter import (
        HermesAdapter,
        HermesAdapterError,
        InvalidTokenError,
        ExpiredTokenError,
        UnauthorizedError,
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

# Global Hermes adapter instance
hermes_adapter = HermesAdapter()


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
        elif self.path.startswith('/hermes/'):
            self._handle_hermes_get()
        else:
            self._send_json(404, {"error": "not_found"})

    def _handle_hermes_get(self):
        """Handle Hermes adapter GET requests."""
        connection_id = self.headers.get('X-Connection-ID', '')

        if not connection_id:
            self._send_json(400, {"error": "missing_connection_id"})
            return

        connection = hermes_adapter.get_connection(connection_id)
        if not connection:
            self._send_json(404, {"error": "connection_not_found"})
            return

        if self.path == '/hermes/status':
            try:
                status = hermes_adapter.read_status(connection)
                self._send_json(200, status)
            except UnauthorizedError as e:
                self._send_json(403, {"error": "unauthorized", "message": str(e)})
            except HermesAdapterError as e:
                self._send_json(400, {"error": "adapter_error", "message": str(e)})
        elif self.path == '/hermes/scope':
            scope = hermes_adapter.get_scope(connection)
            self._send_json(200, {"scope": scope})
        elif self.path == '/hermes/events':
            try:
                events = hermes_adapter.get_hermes_events(connection)
                self._send_json(200, {
                    "events": [asdict(e) for e in events]
                })
            except UnauthorizedError as e:
                self._send_json(403, {"error": "unauthorized", "message": str(e)})
        else:
            self._send_json(404, {"error": "not_found"})

    def _handle_hermes_connect(self, data: dict):
        """Handle Hermes adapter connection request."""
        token = data.get('authority_token')
        if not token:
            self._send_json(400, {"error": "missing_authority_token"})
            return

        try:
            connection = hermes_adapter.connect(token)
            self._send_json(200, {
                "connection_id": connection.connection_id,
                "principal_id": connection.claims.principal_id,
                "capabilities": connection.claims.capabilities,
                "expires_at": connection.claims.expires_at
            })
        except InvalidTokenError as e:
            self._send_json(401, {"error": "invalid_token", "message": str(e)})
        except ExpiredTokenError as e:
            self._send_json(401, {"error": "expired_token", "message": str(e)})
        except HermesAdapterError as e:
            self._send_json(400, {"error": "adapter_error", "message": str(e)})

    def _handle_hermes_summary(self, data: dict):
        """Handle Hermes summary append request."""
        connection_id = data.get('connection_id')
        summary_text = data.get('summary_text')

        if not connection_id:
            self._send_json(400, {"error": "missing_connection_id"})
            return
        if not summary_text:
            self._send_json(400, {"error": "missing_summary_text"})
            return

        connection = hermes_adapter.get_connection(connection_id)
        if not connection:
            self._send_json(404, {"error": "connection_not_found"})
            return

        try:
            event = hermes_adapter.append_summary(connection, summary_text)
            self._send_json(200, {
                "event_id": event.id,
                "created_at": event.created_at
            })
        except UnauthorizedError as e:
            self._send_json(403, {"error": "unauthorized", "message": str(e)})
        except HermesAdapterError as e:
            self._send_json(400, {"error": "adapter_error", "message": str(e)})

    def do_POST(self):
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
        elif self.path == '/hermes/connect':
            self._handle_hermes_connect(data)
        elif self.path == '/hermes/summary':
            self._handle_hermes_summary(data)
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
