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

# Active Hermes connections (in-memory for this demo)
# In production, this would be managed more carefully
active_hermes_connections: Dict[str, 'HermesConnection'] = {}


def _parse_hermes_auth() -> Optional[str]:
    """
    Parse Hermes authorization from request headers.

    Expects: Authorization: Hermes <hermes_id>
    """
    auth_header = None
    for key, value in GatewayHandler.headers_dict.items():
        if key.lower() == 'authorization':
            auth_header = value
            break

    if not auth_header:
        return None

    if auth_header.startswith('Hermes '):
        return auth_header[7:]  # Return hermes_id

    return None


def _get_hermes_connection(hermes_id: str) -> Optional['HermesConnection']:
    """Get active Hermes connection by hermes_id."""
    # Import here to avoid circular dependency
    from hermes import HermesConnection
    return active_hermes_connections.get(hermes_id)


def _store_hermes_connection(connection: 'HermesConnection'):
    """Store an active Hermes connection."""
    active_hermes_connections[connection.hermes_id] = connection


class GatewayHandler(BaseHTTPRequestHandler):
    """HTTP handler for gateway API."""

    # Store headers as dict for easy access
    headers_dict = {}

    def log_message(self, format, *args):
        """Suppress default logging."""
        pass

    def _send_json(self, status: int, data: dict):
        self.send_response(status)
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps(data).encode())

    def _get_json_body(self) -> dict:
        """Parse JSON body from request."""
        content_length = int(self.headers.get('Content-Length', 0))
        body = self.rfile.read(content_length)
        try:
            return json.loads(body) if body else {}
        except json.JSONDecodeError:
            raise ValueError("invalid_json")

    def _check_hermes_control_attempt(self):
        """
        Check if a request appears to be from Hermes attempting control.
        Returns True (blocked) if Hermes is attempting control.
        """
        # Check for Hermes authorization header
        hermes_id = _parse_hermes_auth()
        if hermes_id:
            connection = _get_hermes_connection(hermes_id)
            if connection:
                # Hermes is attempting control - this should be blocked
                return True
        return False

    def do_GET(self):
        # Store headers for this request
        self.headers_dict = {k: v for k, v in self.headers.items()}

        if self.path == '/health':
            self._send_json(200, miner.health)
        elif self.path == '/status':
            self._send_json(200, miner.get_snapshot())
        # Hermes endpoints
        elif self.path == '/hermes/capabilities':
            from hermes import get_capabilities
            self._send_json(200, get_capabilities())
        elif self.path.startswith('/hermes/status'):
            self._handle_hermes_status()
        elif self.path.startswith('/hermes/events'):
            self._handle_hermes_events()
        else:
            self._send_json(404, {"error": "not_found"})

    def do_POST(self):
        # Store headers for this request
        self.headers_dict = {k: v for k, v in self.headers.items()}

        try:
            data = self._get_json_body()
        except ValueError:
            self._send_json(400, {"error": "invalid_json"})
            return

        # Check for Hermes control attempt
        if self.path.startswith('/miner/'):
            if self._check_hermes_control_attempt():
                self._send_json(403, {
                    "error": "HERMES_UNAUTHORIZED",
                    "message": "Hermes agents cannot issue control commands"
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
        # Hermes endpoints
        elif self.path == '/hermes/pair':
            self._handle_hermes_pair(data)
        elif self.path == '/hermes/connect':
            self._handle_hermes_connect(data)
        elif self.path == '/hermes/summary':
            self._handle_hermes_summary(data)
        else:
            self._send_json(404, {"error": "not_found"})

    def _handle_hermes_pair(self, data: dict):
        """Handle Hermes pairing request."""
        from hermes import pair_hermes, HermesAuthError

        hermes_id = data.get('hermes_id')
        device_name = data.get('device_name')

        if not hermes_id:
            self._send_json(400, {"error": "missing_hermes_id"})
            return

        try:
            result = pair_hermes(hermes_id, device_name)
            self._send_json(200, result)
        except ValueError as e:
            self._send_json(400, {"error": str(e)})
        except Exception as e:
            self._send_json(500, {"error": f"pairing_failed: {str(e)}"})

    def _handle_hermes_connect(self, data: dict):
        """Handle Hermes connection with authority token."""
        from hermes import (
            connect, HermesAuthError, HermesCapabilityError, _store_hermes_connection
        )

        authority_token = data.get('authority_token')

        if not authority_token:
            self._send_json(400, {"error": "missing_authority_token"})
            return

        try:
            connection = connect(authority_token)
            _store_hermes_connection(connection)
            self._send_json(200, connection.to_dict())
        except HermesAuthError as e:
            self._send_json(401, {"error": str(e)})
        except Exception as e:
            self._send_json(500, {"error": f"connection_failed: {str(e)}"})

    def _handle_hermes_status(self):
        """Handle Hermes status read request."""
        from hermes import (
            read_status, HermesCapabilityError,
            HermesAuthError, HermesConnection
        )

        hermes_id = _parse_hermes_auth()
        if not hermes_id:
            self._send_json(401, {"error": "missing_hermes_authorization"})
            return

        connection = _get_hermes_connection(hermes_id)
        if not connection:
            self._send_json(401, {"error": "hermes_not_connected"})
            return

        try:
            status = read_status(connection)
            self._send_json(200, status)
        except HermesCapabilityError as e:
            self._send_json(403, {"error": str(e)})
        except Exception as e:
            self._send_json(500, {"error": f"status_read_failed: {str(e)}"})

    def _handle_hermes_summary(self, data: dict):
        """Handle Hermes summary append request."""
        from hermes import (
            append_summary, HermesCapabilityError, HermesAuthError
        )

        hermes_id = _parse_hermes_auth()
        if not hermes_id:
            self._send_json(401, {"error": "missing_hermes_authorization"})
            return

        connection = _get_hermes_connection(hermes_id)
        if not connection:
            self._send_json(401, {"error": "hermes_not_connected"})
            return

        summary_text = data.get('summary_text')
        authority_scope = data.get('authority_scope', ['observe'])

        if not summary_text:
            self._send_json(400, {"error": "missing_summary_text"})
            return

        try:
            result = append_summary(connection, summary_text, authority_scope)
            self._send_json(200, result)
        except HermesCapabilityError as e:
            self._send_json(403, {"error": str(e)})
        except ValueError as e:
            self._send_json(400, {"error": str(e)})
        except Exception as e:
            self._send_json(500, {"error": f"summary_append_failed: {str(e)}"})

    def _handle_hermes_events(self):
        """Handle Hermes filtered events request."""
        from hermes import get_filtered_events, HermesAuthError

        hermes_id = _parse_hermes_auth()
        if not hermes_id:
            self._send_json(401, {"error": "missing_hermes_authorization"})
            return

        connection = _get_hermes_connection(hermes_id)
        if not connection:
            self._send_json(401, {"error": "hermes_not_connected"})
            return

        # Parse limit from query params
        limit = 20
        if '?' in self.path:
            query = self.path.split('?', 1)[1]
            for param in query.split('&'):
                if param.startswith('limit='):
                    try:
                        limit = int(param.split('=', 1)[1])
                    except ValueError:
                        pass

        try:
            events = get_filtered_events(connection, limit)
            self._send_json(200, {"events": events})
        except Exception as e:
            self._send_json(500, {"error": f"events_fetch_failed: {str(e)}"})


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
