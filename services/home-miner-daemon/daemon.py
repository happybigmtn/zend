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
from typing import Optional, Tuple

# Hermes adapter — must be imported after environment is set up
import hermes as hermes_adapter


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

    # ------------------------------------------------------------------
    # Hermes Auth Helper
    # ------------------------------------------------------------------

    def _parse_hermes_auth(self) -> Tuple[Optional[str], Optional[str]]:
        """
        Parse the Hermes auth header: Authorization: Hermes <hermes_id>

        Returns:
            (hermes_id, error_code).  hermes_id is None on error.
        """
        auth = self.headers.get('Authorization', '')
        if not auth.startswith('Hermes '):
            return None, 'HERMES_AUTH_REQUIRED'

        hermes_id = auth[len('Hermes '):].strip()
        if not hermes_id:
            return None, 'HERMES_ID_REQUIRED'

        if not hermes_adapter.is_hermes_paired(hermes_id):
            return None, 'HERMES_NOT_PAIRED'

        return hermes_id, None

    def _require_hermes_connection(self) -> Optional[hermes_adapter.HermesConnection]:
        """
        Parse the authority token from request body and return a HermesConnection.
        Sends an error response and returns None if validation fails.
        """
        content_len = int(self.headers.get('Content-Length', 0))
        if content_len == 0:
            self._send_json(400, {
                "error": "HERMES_BODY_REQUIRED",
                "message": "Request body must contain authority_token"
            })
            return None

        body = self.rfile.read(content_len)
        try:
            data = json.loads(body)
        except json.JSONDecodeError:
            self._send_json(400, {"error": "HERMES_INVALID_JSON",
                                  "message": "Request body must be valid JSON"})
            return None

        token = data.get('authority_token', '')
        try:
            return hermes_adapter.connect(token)
        except PermissionError as exc:
            self._send_json(403, {"error": "HERMES_UNAUTHORIZED",
                                  "message": str(exc)})
            return None
        except ValueError as exc:
            self._send_json(401, {"error": "HERMES_TOKEN_INVALID",
                                  "message": str(exc)})
            return None

    # ------------------------------------------------------------------
    # Hermes Endpoints
    # ------------------------------------------------------------------

    def do_POST(self):
        if self.path.startswith('/hermes/'):
            self._handle_hermes_post()
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
        else:
            self._send_json(404, {"error": "not_found"})

    def _handle_hermes_post(self):
        """Route Hermes POST requests to the appropriate handler."""
        if self.path == '/hermes/pair':
            self._hermes_pair()
        elif self.path == '/hermes/connect':
            self._hermes_connect_endpoint()
        elif self.path == '/hermes/summary':
            self._hermes_summary()
        else:
            self._send_json(404, {"error": "not_found"})

    def _hermes_pair(self):
        """POST /hermes/pair — register a Hermes agent with observe+summarize."""
        content_len = int(self.headers.get('Content-Length', 0))
        body = self.rfile.read(content_len) if content_len > 0 else b'{}'
        try:
            data = json.loads(body)
        except json.JSONDecodeError:
            self._send_json(400, {"error": "HERMES_INVALID_JSON",
                                  "message": "Request body must be valid JSON"})
            return

        hermes_id = data.get('hermes_id', '')
        device_name = data.get('device_name', f"hermes-{hermes_id}")

        if not hermes_id:
            self._send_json(400, {"error": "HERMES_ID_REQUIRED",
                                  "message": "hermes_id is required"})
            return

        record = hermes_adapter.pair(hermes_id, device_name)
        self._send_json(200, {
            "success": True,
            "hermes_id": record["hermes_id"],
            "device_name": record["device_name"],
            "principal_id": record["principal_id"],
            "capabilities": record["capabilities"],
            "paired_at": record["paired_at"],
        })

    def _hermes_connect_endpoint(self):
        """POST /hermes/connect — validate token and return connection info + fresh token."""
        conn = self._require_hermes_connection()
        if conn is None:
            return  # Error already sent

        fresh_token = hermes_adapter.issue_authority_token(
            conn.hermes_id,
            conn.principal_id,
            conn.capabilities,
        )
        self._send_json(200, {
            "connected": True,
            "hermes_id": conn.hermes_id,
            "principal_id": conn.principal_id,
            "capabilities": conn.capabilities,
            "connected_at": conn.connected_at,
            "authority_token": fresh_token,
        })

    def _hermes_summary(self):
        """POST /hermes/summary — append a Hermes summary to the event spine."""
        hermes_id, err = self._parse_hermes_auth()
        if err:
            self._send_json(401, {"error": err,
                                  "message": f"Authorization: Hermes <hermes_id> header required: {err}"})
            return

        conn = self._require_hermes_connection()
        if conn is None:
            return  # Error already sent

        content_len = int(self.headers.get('Content-Length', 0))
        if content_len == 0:
            self._send_json(400, {"error": "HERMES_BODY_REQUIRED",
                                  "message": "summary_text and authority_scope required in body"})
            return

        body = self.rfile.read(content_len)
        try:
            data = json.loads(body)
        except json.JSONDecodeError:
            self._send_json(400, {"error": "HERMES_INVALID_JSON", "message": "Invalid JSON"})
            return

        summary_text = data.get('summary_text', '')
        authority_scope = data.get('authority_scope', 'observe')

        try:
            event = hermes_adapter.append_summary(conn, summary_text, authority_scope)
            self._send_json(200, {
                "appended": True,
                "event_id": event["id"],
                "kind": event["kind"],
                "created_at": event["created_at"],
            })
        except PermissionError as exc:
            self._send_json(403, {"error": "HERMES_UNAUTHORIZED", "message": str(exc)})
        except ValueError as exc:
            self._send_json(400, {"error": "HERMES_INVALID_SUMMARY", "message": str(exc)})

    def do_GET(self):
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
        """Route Hermes GET requests to the appropriate handler."""
        if self.path == '/hermes/status':
            self._hermes_status()
        elif self.path == '/hermes/events':
            self._hermes_events()
        else:
            self._send_json(404, {"error": "not_found"})

    def _hermes_status(self):
        """GET /hermes/status — read miner status through Hermes adapter."""
        hermes_id, err = self._parse_hermes_auth()
        if err:
            self._send_json(401, {"error": err,
                                  "message": f"Authorization: Hermes <hermes_id> header required: {err}"})
            return

        conn = self._require_hermes_connection()
        if conn is None:
            return  # Error already sent

        try:
            status = hermes_adapter.read_status(conn)
            self._send_json(200, status)
        except PermissionError as exc:
            self._send_json(403, {"error": "HERMES_UNAUTHORIZED", "message": str(exc)})

    def _hermes_events(self):
        """GET /hermes/events — read filtered events (no user_message)."""
        hermes_id, err = self._parse_hermes_auth()
        if err:
            self._send_json(401, {"error": err,
                                  "message": f"Authorization: Hermes <hermes_id> header required: {err}"})
            return

        conn = self._require_hermes_connection()
        if conn is None:
            return  # Error already sent

        # Parse optional limit param: /hermes/events?limit=10
        limit = 20
        if '?' in self.path:
            query = self.path.split('?', 1)[1]
            for param in query.split('&'):
                if param.startswith('limit='):
                    try:
                        limit = max(1, int(param.split('=', 1)[1]))
                    except ValueError:
                        pass

        events = hermes_adapter.get_filtered_events(conn, limit=limit)
        self._send_json(200, {"events": events, "count": len(events)})


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
