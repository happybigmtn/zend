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

import hermes as hermes_adapter
from store import load_or_create_principal


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
        elif self.path.startswith('/hermes/'):
            self._handle_hermes_get()
        else:
            self._send_json(404, {"error": "not_found"})

    def _handle_hermes_get(self):
        """Route Hermes GET requests to appropriate handlers."""
        auth_header = self.headers.get('Authorization', '')

        if not hermes_adapter.is_hermes_auth_header(auth_header):
            self._send_json(401, {"error": "HERMES_UNAUTHORIZED", "message": "Missing Hermes Authorization header"})
            return

        hermes_id = hermes_adapter.extract_hermes_id_from_header(auth_header)
        if not hermes_id:
            self._send_json(401, {"error": "HERMES_UNAUTHORIZED", "message": "Malformed Hermes Authorization header"})
            return

        # Token is passed in X-Hermes-Token header for GET requests
        token = self.headers.get('X-Hermes-Token', '')

        if self.path == '/hermes/status':
            self._hermes_read_status(hermes_id, token)
        elif self.path == '/hermes/events':
            self._hermes_get_events(hermes_id, token)
        elif self.path == '/hermes/connection':
            self._hermes_get_connection(hermes_id, token)
        else:
            self._send_json(404, {"error": "not_found"})

    def _get_hermes_connection(self, hermes_id: str, token: str):
        """
        Validate a Hermes token and return a HermesConnection.
        Returns (HermesConnection, error_response_tuple) where error_response_tuple
        is None on success.
        """
        if not token:
            return None, (401, {"error": "HERMES_UNAUTHORIZED", "message": "Missing X-Hermes-Token header"})

        try:
            connection = hermes_adapter.connect(token)
            return connection, None
        except ValueError as e:
            msg = str(e)
            code = "HERMES_INVALID_TOKEN"
            if "EXPIRED" in msg:
                code = "HERMES_TOKEN_EXPIRED"
            elif "NOT_PAIRED" in msg:
                code = "HERMES_NOT_PAIRED"
            return None, (401, {"error": code, "message": msg})
        except hermes_adapter.HermesPermissionError as e:
            return None, (403, {"error": e.code, "message": str(e)})

    def _hermes_read_status(self, hermes_id: str, token: str):
        """GET /hermes/status — read miner status through adapter."""
        connection, err = self._get_hermes_connection(hermes_id, token)
        if err:
            status, body = err
            self._send_json(status, body)
            return

        try:
            status = hermes_adapter.read_status(
                connection,
                miner_snapshot_fn=miner.get_snapshot
            )
            self._send_json(200, {
                "hermes_id": connection.hermes_id,
                "status": status,
            })
        except hermes_adapter.HermesPermissionError as e:
            self._send_json(403, {"error": e.code, "message": str(e)})
        except PermissionError:
            self._send_json(403, {"error": "HERMES_UNAUTHORIZED", "message": "observe capability required"})

    def _hermes_get_events(self, hermes_id: str, token: str):
        """GET /hermes/events — read filtered events (no user_message)."""
        connection, err = self._get_hermes_connection(hermes_id, token)
        if err:
            status, body = err
            self._send_json(status, body)
            return

        try:
            events = hermes_adapter.get_filtered_events(connection, limit=20)
            self._send_json(200, {
                "hermes_id": connection.hermes_id,
                "events": events,
                "count": len(events),
            })
        except hermes_adapter.HermesPermissionError as e:
            self._send_json(403, {"error": e.code, "message": str(e)})

    def _hermes_get_connection(self, hermes_id: str, token: str):
        """GET /hermes/connection — return current connection state."""
        connection, err = self._get_hermes_connection(hermes_id, token)
        if err:
            status, body = err
            self._send_json(status, body)
            return

        self._send_json(200, {
            "connected": True,
            **connection.to_dict(),
        })

    def do_POST(self):
        content_length = int(self.headers.get('Content-Length', 0))
        body = self.rfile.read(content_length)

        try:
            data = json.loads(body) if body else {}
        except json.JSONDecodeError:
            self._send_json(400, {"error": "invalid_json"})
            return

        # Hermes endpoints first (they have their own auth)
        if self.path.startswith('/hermes/'):
            self._handle_hermes_post(data)
            return

        # Gateway control endpoints — reject Hermes auth
        auth_header = self.headers.get('Authorization', '')
        if hermes_adapter.is_hermes_auth_header(auth_header):
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

    def _handle_hermes_post(self, data: dict):
        """Route Hermes POST requests to appropriate handlers."""
        if self.path == '/hermes/pair':
            self._hermes_pair(data)
        elif self.path == '/hermes/connect':
            self._hermes_connect(data)
        elif self.path == '/hermes/summary':
            self._hermes_append_summary(data)
        else:
            self._send_json(404, {"error": "not_found"})

    def _hermes_pair(self, data: dict):
        """
        POST /hermes/pair — Create or update a Hermes pairing record.

        This does not require an authority token; it creates one.
        Response includes the token Hermes should use for /hermes/connect.
        """
        hermes_id = data.get('hermes_id')
        device_name = data.get('device_name', hermes_id or 'hermes-agent')

        if not hermes_id:
            self._send_json(400, {"error": "missing_hermes_id"})
            return

        principal = load_or_create_principal()

        pairing = hermes_adapter.pair_hermes(
            hermes_id=hermes_id,
            device_name=device_name,
            principal_id=principal.id,
        )

        # Issue authority token with Hermes capabilities
        token = hermes_adapter.issue_authority_token(
            hermes_id=hermes_id,
            principal_id=principal.id,
            capabilities=hermes_adapter.HERMES_CAPABILITIES,
        )

        self._send_json(200, {
            "paired": True,
            "hermes_id": pairing.hermes_id,
            "device_name": pairing.device_name,
            "principal_id": principal.id,
            "capabilities": pairing.capabilities,
            "paired_at": pairing.paired_at,
            "token": token.token,
            "token_expires_at": token.expires_at,
            "connect_instruction": "Use POST /hermes/connect with the token to establish a session",
        })

    def _hermes_connect(self, data: dict):
        """
        POST /hermes/connect — Establish a Hermes session from authority token.

        Validates the token and returns connection metadata.
        """
        token_str = data.get('token') or self.headers.get('Authorization', '').replace('Bearer ', '')

        if not token_str:
            self._send_json(400, {"error": "missing_token", "message": "Authority token required"})
            return

        try:
            connection = hermes_adapter.connect(token_str)
            self._send_json(200, {
                "connected": True,
                **connection.to_dict(),
            })
        except ValueError as e:
            msg = str(e)
            code = "HERMES_INVALID_TOKEN"
            if "EXPIRED" in msg:
                code = "HERMES_TOKEN_EXPIRED"
            elif "NOT_PAIRED" in msg:
                code = "HERMES_NOT_PAIRED"
            self._send_json(401, {"error": code, "message": msg})

    def _hermes_append_summary(self, data: dict):
        """
        POST /hermes/summary — Append a Hermes summary to the event spine.

        Requires summarize capability. Returns the appended event details.
        """
        summary_text = data.get('summary_text')
        authority_scope = data.get('authority_scope', 'observe')

        if not summary_text:
            self._send_json(400, {"error": "missing_summary_text"})
            return

        # Get connection from Bearer token in Authorization header
        connection, err = self._get_hermes_connection_from_token(data)
        if err:
            status, body = err
            self._send_json(status, body)
            return

        try:
            result = hermes_adapter.append_summary(
                connection=connection,
                summary_text=summary_text,
                authority_scope=authority_scope,
            )
            self._send_json(200, {
                "appended": True,
                "event_id": result["event_id"],
                "kind": result["kind"],
                "created_at": result["created_at"],
            })
        except hermes_adapter.HermesPermissionError as e:
            self._send_json(403, {"error": e.code, "message": str(e)})
        except PermissionError:
            self._send_json(403, {"error": "HERMES_UNAUTHORIZED", "message": "summarize capability required"})

    def _get_hermes_connection_from_token(self, data: dict):
        """
        Retrieve HermesConnection from token in request body or Authorization header.
        Returns (connection, error_tuple) where error_tuple is None on success.
        """
        token_str = data.get('token', '')
        if not token_str:
            auth_header = self.headers.get('Authorization', '')
            if auth_header.startswith('Bearer '):
                token_str = auth_header[7:]

        if not token_str:
            return None, (400, {"error": "missing_token", "message": "Authority token required"})

        try:
            connection = hermes_adapter.connect(token_str)
            return connection, None
        except ValueError as e:
            msg = str(e)
            code = "HERMES_INVALID_TOKEN"
            if "EXPIRED" in msg:
                code = "HERMES_TOKEN_EXPIRED"
            elif "NOT_PAIRED" in msg:
                code = "HERMES_NOT_PAIRED"
            return None, (401, {"error": code, "message": msg})
        except hermes_adapter.HermesPermissionError as e:
            return None, (403, {"error": e.code, "message": str(e)})


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
