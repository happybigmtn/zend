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
from typing import Optional, Dict

# Import Hermes adapter
import hermes
from hermes import (
    HermesConnection,
    HermesAuthenticationError,
    HermesCapabilityError,
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

    def _check_hermes_control(self) -> Optional[Dict]:
        """
        Check if a request is from Hermes trying to use control.
        Returns error dict if Hermes, None otherwise.
        """
        auth_header = self.headers.get('Authorization', '')

        # Check for Hermes auth header pattern
        hermes_match = re.match(r'^Hermes\s+(\S+)$', auth_header)
        if hermes_match:
            hermes_id = hermes_match.group(1)
            return {
                "error": "HERMES_UNAUTHORIZED",
                "message": "Hermes does not have control capability. Control commands are not permitted for Hermes agents.",
                "hermes_id": hermes_id,
            }
        return None

    def do_GET(self):
        if self.path == '/health':
            self._send_json(200, miner.health)
        elif self.path == '/status':
            self._send_json(200, miner.get_snapshot())
        elif self.path.startswith('/hermes/'):
            # Delegate to Hermes handler
            HermesHandler.handle_request(self, 'GET')
        else:
            self._send_json(404, {"error": "not_found"})

    def do_POST(self):
        # Check if Hermes is attempting control
        hermes_error = self._check_hermes_control()
        if hermes_error:
            self._send_json(403, hermes_error)
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
        elif self.path.startswith('/hermes/'):
            # Delegate to Hermes handler
            HermesHandler.handle_request(self, 'POST', data)
        else:
            self._send_json(404, {"error": "not_found"})


class HermesHandler:
    """
    HTTP handler for Hermes adapter endpoints.

    Hermes can observe miner status and append summaries, but cannot control.
    All Hermes requests must include Authorization: Hermes <hermes_id> header.
    """

    # Thread-safe connection storage
    _connections: Dict[str, HermesConnection] = {}
    _lock = threading.Lock()

    @classmethod
    def _get_hermes_id(cls, handler: GatewayHandler) -> Optional[str]:
        """Extract hermes_id from Authorization header."""
        auth_header = handler.headers.get('Authorization', '')
        match = re.match(r'^Hermes\s+(\S+)$', auth_header)
        return match.group(1) if match else None

    @classmethod
    def _send_json(cls, handler: GatewayHandler, status: int, data: dict):
        handler.send_response(status)
        handler.send_header('Content-Type', 'application/json')
        handler.end_headers()
        handler.wfile.write(json.dumps(data).encode())

    @classmethod
    def _require_auth(cls, handler: GatewayHandler) -> Optional[str]:
        """Require Hermes authorization, return hermes_id or send error."""
        hermes_id = cls._get_hermes_id(handler)
        if not hermes_id:
            cls._send_json(handler, 401, {
                "error": "UNAUTHORIZED",
                "message": "Missing or invalid Authorization header. Expected: Hermes <hermes_id>",
            })
            return None
        return hermes_id

    @classmethod
    def _get_connection(cls, hermes_id: str) -> Optional[HermesConnection]:
        """Get active connection for hermes_id."""
        with cls._lock:
            return cls._connections.get(hermes_id)

    @classmethod
    def _set_connection(cls, hermes_id: str, connection: HermesConnection):
        """Set active connection for hermes_id."""
        with cls._lock:
            cls._connections[hermes_id] = connection

    @classmethod
    def handle_request(cls, handler: GatewayHandler, method: str, data: dict = None):
        """Route Hermes requests to appropriate handler method."""
        path = handler.path.replace('/hermes/', '')

        if path == 'pair' and method == 'POST':
            cls.handle_pair(handler, data or {})
        elif path == 'connect' and method == 'POST':
            cls.handle_connect(handler, data or {})
        elif path == 'status' and method == 'GET':
            cls.handle_status(handler)
        elif path == 'summary' and method == 'POST':
            cls.handle_summary(handler, data or {})
        elif path == 'events' and method == 'GET':
            cls.handle_events(handler)
        else:
            cls._send_json(handler, 404, {"error": "not_found"})

    @classmethod
    def handle_pair(cls, handler: GatewayHandler, data: dict):
        """
        POST /hermes/pair
        Create or update Hermes pairing record.
        """
        hermes_id = data.get('hermes_id')
        device_name = data.get('device_name')

        if not hermes_id:
            cls._send_json(handler, 400, {
                "error": "MISSING_HERMES_ID",
                "message": "hermes_id is required",
            })
            return

        try:
            pairing = hermes.pair_hermes(hermes_id, device_name)
            cls._send_json(handler, 200, {
                "success": True,
                "hermes_id": pairing['hermes_id'],
                "capabilities": pairing['capabilities'],
                "device_name": pairing['device_name'],
                "paired_at": pairing['paired_at'],
            })
        except Exception as e:
            cls._send_json(handler, 500, {
                "error": "PAIRING_FAILED",
                "message": str(e),
            })

    @classmethod
    def handle_connect(cls, handler: GatewayHandler, data: dict):
        """
        POST /hermes/connect
        Accept authority token and establish connection.
        """
        authority_token = data.get('authority_token')

        if not authority_token:
            cls._send_json(handler, 400, {
                "error": "MISSING_TOKEN",
                "message": "authority_token is required",
            })
            return

        try:
            connection = hermes.connect(authority_token)
            cls._set_connection(connection.hermes_id, connection)

            cls._send_json(handler, 200, {
                "connected": True,
                "hermes_id": connection.hermes_id,
                "principal_id": connection.principal_id,
                "capabilities": connection.capabilities,
                "connected_at": connection.connected_at,
            })
        except HermesAuthenticationError as e:
            cls._send_json(handler, 401, {
                "error": "AUTHENTICATION_FAILED",
                "message": str(e),
            })
        except HermesCapabilityError as e:
            cls._send_json(handler, 403, {
                "error": "CAPABILITY_ERROR",
                "message": str(e),
            })
        except Exception as e:
            cls._send_json(handler, 500, {
                "error": "CONNECTION_FAILED",
                "message": str(e),
            })

    @classmethod
    def handle_status(cls, handler: GatewayHandler):
        """
        GET /hermes/status
        Read miner status through adapter (requires Hermes auth).
        """
        hermes_id = cls._require_auth(handler)
        if not hermes_id:
            return

        connection = cls._get_connection(hermes_id)
        if not connection:
            cls._send_json(handler, 401, {
                "error": "NOT_CONNECTED",
                "message": "Hermes is not connected. Call POST /hermes/connect first.",
            })
            return

        try:
            status = hermes.read_status(connection)
            cls._send_json(handler, 200, status)
        except HermesCapabilityError as e:
            cls._send_json(handler, 403, {
                "error": "HERMES_UNAUTHORIZED",
                "message": str(e),
            })
        except Exception as e:
            cls._send_json(handler, 500, {
                "error": "STATUS_FAILED",
                "message": str(e),
            })

    @classmethod
    def handle_summary(cls, handler: GatewayHandler, data: dict):
        """
        POST /hermes/summary
        Append a summary to the event spine (requires Hermes auth).
        """
        hermes_id = cls._require_auth(handler)
        if not hermes_id:
            return

        connection = cls._get_connection(hermes_id)
        if not connection:
            cls._send_json(handler, 401, {
                "error": "NOT_CONNECTED",
                "message": "Hermes is not connected. Call POST /hermes/connect first.",
            })
            return

        summary_text = data.get('summary_text')
        authority_scope = data.get('authority_scope', 'observe')

        if not summary_text:
            cls._send_json(handler, 400, {
                "error": "MISSING_SUMMARY",
                "message": "summary_text is required",
            })
            return

        try:
            event = hermes.append_summary(connection, summary_text, authority_scope)
            cls._send_json(handler, 200, {
                "appended": True,
                "event_id": event.id,
                "kind": event.kind,
                "created_at": event.created_at,
            })
        except HermesCapabilityError as e:
            cls._send_json(handler, 403, {
                "error": "HERMES_UNAUTHORIZED",
                "message": str(e),
            })
        except ValueError as e:
            cls._send_json(handler, 400, {
                "error": "INVALID_SUMMARY",
                "message": str(e),
            })
        except Exception as e:
            cls._send_json(handler, 500, {
                "error": "SUMMARY_FAILED",
                "message": str(e),
            })

    @classmethod
    def handle_events(cls, handler: GatewayHandler):
        """
        GET /hermes/events
        Read filtered events (no user_message).
        """
        hermes_id = cls._require_auth(handler)
        if not hermes_id:
            return

        connection = cls._get_connection(hermes_id)
        if not connection:
            cls._send_json(handler, 401, {
                "error": "NOT_CONNECTED",
                "message": "Hermes is not connected. Call POST /hermes/connect first.",
            })
            return

        try:
            events = hermes.get_filtered_events(connection, limit=20)
            cls._send_json(handler, 200, {
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
        except Exception as e:
            cls._send_json(handler, 500, {
                "error": "EVENTS_FAILED",
                "message": str(e),
            })


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
