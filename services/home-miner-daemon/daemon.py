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
    HermesError,
    HermesUnauthorizedError,
    HermesInvalidTokenError,
    pair_hermes,
    get_hermes_pairing,
    connect as hermes_connect,
    read_status as hermes_read_status,
    append_summary as hermes_append_summary,
    get_filtered_events as hermes_get_filtered_events,
    is_hermes_request,
    validate_hermes_auth,
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


class HermesHandler(BaseHTTPRequestHandler):
    """HTTP handler for Hermes adapter API."""

    def log_message(self, format, *args):
        """Suppress default logging."""
        pass

    def _send_json(self, status: int, data: dict):
        self.send_response(status)
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps(data).encode())

    def _get_hermes_connection(self) -> HermesConnection:
        """Validate Hermes auth and return connection."""
        headers = {k: v for k, v in self.headers.items()}
        return validate_hermes_auth(headers)

    def do_POST(self):
        content_length = int(self.headers.get('Content-Length', 0))
        body = self.rfile.read(content_length)

        try:
            data = json.loads(body) if body else {}
        except json.JSONDecodeError:
            self._send_json(400, {"error": "invalid_json"})
            return

        if self.path == '/hermes/pair':
            # Create new Hermes pairing
            hermes_id = data.get('hermes_id')
            if not hermes_id:
                self._send_json(400, {"error": "missing_hermes_id"})
                return
            
            device_name = data.get('device_name')
            pairing = pair_hermes(hermes_id, device_name)
            
            self._send_json(200, {
                "hermes_id": pairing.hermes_id,
                "device_name": pairing.device_name,
                "capabilities": pairing.capabilities,
                "paired_at": pairing.paired_at,
                "token": pairing.token,
            })

        elif self.path == '/hermes/connect':
            # Connect with authority token
            authority_token = data.get('authority_token')
            hermes_id = data.get('hermes_id')
            
            if not authority_token:
                self._send_json(400, {"error": "missing_authority_token"})
                return
            
            try:
                connection = hermes_connect(authority_token, hermes_id)
                self._send_json(200, {
                    "connected": True,
                    "hermes_id": connection.hermes_id,
                    "capabilities": connection.capabilities,
                    "authority_scope": connection.authority_scope,
                    "connected_at": connection.connected_at,
                })
            except HermesInvalidTokenError as e:
                self._send_json(401, {"error": "invalid_token", "message": str(e)})
            except HermesError as e:
                self._send_json(403, {"error": "unauthorized", "message": str(e)})

        elif self.path == '/hermes/summary':
            # Append summary to spine
            try:
                connection = self._get_hermes_connection()
            except HermesUnauthorizedError as e:
                self._send_json(403, {"error": "hermes_unauthorized", "message": str(e)})
                return

            summary_text = data.get('summary_text')
            if not summary_text:
                self._send_json(400, {"error": "missing_summary_text"})
                return

            authority_scope = data.get('authority_scope')
            event = hermes_append_summary(connection, summary_text, authority_scope)

            self._send_json(200, {
                "appended": True,
                "event_id": event.id,
                "kind": event.kind,
                "generated_at": event.payload.get('generated_at'),
            })

        else:
            self._send_json(404, {"error": "not_found"})

    def do_GET(self):
        if self.path == '/hermes/status':
            # Read miner status through adapter
            try:
                connection = self._get_hermes_connection()
            except HermesUnauthorizedError as e:
                self._send_json(403, {"error": "hermes_unauthorized", "message": str(e)})
                return

            status = hermes_read_status(connection)
            self._send_json(200, {
                "miner_status": status,
                "capabilities": connection.capabilities,
                "authority_scope": connection.authority_scope,
            })

        elif self.path == '/hermes/events':
            # Read filtered events
            try:
                connection = self._get_hermes_connection()
            except HermesUnauthorizedError as e:
                self._send_json(403, {"error": "hermes_unauthorized", "message": str(e)})
                return

            limit = 20
            if 'limit' in self.path:
                # Parse ?limit=N if present
                parts = self.path.split('?')
                if len(parts) > 1:
                    for param in parts[1].split('&'):
                        if param.startswith('limit='):
                            try:
                                limit = int(param.split('=')[1])
                            except ValueError:
                                pass

            events = hermes_get_filtered_events(connection, limit)
            
            self._send_json(200, {
                "events": [
                    {
                        "id": e.id,
                        "kind": e.kind,
                        "payload": e.payload,
                        "created_at": e.created_at,
                    }
                    for e in events
                ],
                "count": len(events),
            })

        else:
            self._send_json(404, {"error": "not_found"})


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

    def _check_hermes_control_attempt(self):
        """Block Hermes from issuing control commands."""
        headers = {k: v for k, v in self.headers.items()}
        if is_hermes_request(headers):
            self._send_json(403, {
                "error": "hermes_unauthorized",
                "message": "HERMES_UNAUTHORIZED: Hermes cannot issue control commands"
            })
            return True
        return False

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

        if self.path == '/miner/start':
            # Block Hermes control attempts
            if self._check_hermes_control_attempt():
                return
            result = miner.start()
            self._send_json(200 if result["success"] else 400, result)
        elif self.path == '/miner/stop':
            # Block Hermes control attempts
            if self._check_hermes_control_attempt():
                return
            result = miner.stop()
            self._send_json(200 if result["success"] else 400, result)
        elif self.path == '/miner/set_mode':
            # Block Hermes control attempts
            if self._check_hermes_control_attempt():
                return
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


class RoutingHandler(BaseHTTPRequestHandler):
    """Router that delegates to HermesHandler or GatewayHandler based on path."""
    
    def log_message(self, format, *args):
        """Suppress default logging."""
        pass

    def _route(self):
        """Route request to appropriate handler."""
        # Hermes endpoints
        if self.path.startswith('/hermes/'):
            return HermesHandler
        # Gateway endpoints
        elif self.path.startswith('/miner/') or self.path in ['/health', '/status']:
            return GatewayHandler
        else:
            return GatewayHandler
    
    def do_GET(self):
        handler_class = self._route()
        handler = handler_class(self.request, self.client_address, self.server)
        handler.do_GET()
    
    def do_POST(self):
        handler_class = self._route()
        handler = handler_class(self.request, self.client_address, self.server)
        handler.do_POST()


def run_server(host: str = BIND_HOST, port: int = BIND_PORT):
    """Run the gateway server."""
    server = ThreadedHTTPServer((host, port), RoutingHandler)
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
