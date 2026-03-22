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
    """HTTP handler for gateway API including Hermes adapter endpoints."""

    def log_message(self, format, *args):
        """Suppress default logging."""
        pass

    def _send_json(self, status: int, data: dict):
        self.send_response(status)
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps(data).encode())

    def _send_error(self, status: int, code: str, message: str):
        self._send_json(status, {"error": code, "message": message})

    def _require_hermes_auth(self):
        """
        Parse and validate the Hermes Authorization header.

        Header format: Authorization: Hermes <hermes_id>

        Returns the HermesConnection on success, or sends a 401/403
        and returns None on failure.
        """
        import hermes as _hermes

        auth_header = self.headers.get('Authorization', '')
        if not auth_header.startswith('Hermes '):
            self._send_error(401, 'HERMES_UNAUTHORIZED',
                             'Missing or malformed Hermes authorization header')
            return None

        hermes_id = auth_header[7:].strip()
        if not hermes_id:
            self._send_error(401, 'HERMES_UNAUTHORIZED', 'Hermes ID is required')
            return None

        connection = _hermes.get_hermes_pairing(hermes_id)
        if connection is None:
            self._send_error(403, 'HERMES_UNAUTHORIZED',
                             f'No pairing found for Hermes ID: {hermes_id}')
            return None

        return connection

    # ------------------------------------------------------------------
    # Hermes adapter endpoints
    # ------------------------------------------------------------------

    def do_GET(self):
        # Health and status endpoints
        if self.path == '/health':
            self._send_json(200, miner.health)
        elif self.path == '/status':
            self._send_json(200, miner.get_snapshot())

        # Hermes filtered events — requires Hermes auth
        elif self.path.startswith('/hermes/events'):
            import hermes as _hermes
            connection = self._require_hermes_auth()
            if connection is None:
                return

            limit = 20
            if '?' in self.path:
                import urllib.parse
                qs = urllib.parse.parse_qs(self.path.split('?', 1)[1])
                limit = int(qs.get('limit', [20])[0])

            events = _hermes.get_filtered_events(connection, limit=limit)
            self._send_json(200, {"events": events, "count": len(events)})

        # Hermes status — requires Hermes auth + observe capability
        elif self.path == '/hermes/status':
            import hermes as _hermes
            connection = self._require_hermes_auth()
            if connection is None:
                return

            try:
                status = _hermes.read_status(connection)
                self._send_json(200, status)
            except PermissionError as exc:
                self._send_error(403, 'HERMES_UNAUTHORIZED', str(exc))

        else:
            self._send_json(404, {"error": "not_found"})

    def do_POST(self):
        import hermes as _hermes

        content_length = int(self.headers.get('Content-Length', 0))
        body = self.rfile.read(content_length)

        try:
            data = json.loads(body) if body else {}
        except json.JSONDecodeError:
            self._send_error(400, 'INVALID_JSON', 'Request body must be valid JSON')
            return

        # ── Hermes adapter routes ───────────────────────────────────────

        # POST /hermes/connect  — validate authority token
        if self.path == '/hermes/connect':
            token = data.get('authority_token', '')
            if not token:
                self._send_error(400, 'MISSING_TOKEN', 'authority_token is required')
                return

            try:
                connection = _hermes.connect(token)
                self._send_json(200, connection.to_dict())
            except ValueError as exc:
                self._send_error(401, 'HERMES_UNAUTHORIZED', str(exc))

        # POST /hermes/pair  — create Hermes pairing record
        elif self.path == '/hermes/pair':
            hermes_id = data.get('hermes_id', '')
            device_name = data.get('device_name', f'hermes-{hermes_id}')

            if not hermes_id:
                self._send_error(400, 'MISSING_HERMES_ID', 'hermes_id is required')
                return

            connection = _hermes.pair_hermes(hermes_id, device_name)
            self._send_json(200, connection.to_dict())

        # POST /hermes/summary  — append Hermes summary (requires summarize cap)
        elif self.path == '/hermes/summary':
            connection = self._require_hermes_auth()
            if connection is None:
                return

            summary_text = data.get('summary_text', '')
            if not summary_text:
                self._send_error(400, 'MISSING_SUMMARY', 'summary_text is required')
                return

            authority_scope = data.get('authority_scope')
            try:
                result = _hermes.append_summary(connection, summary_text, authority_scope)
                self._send_json(200, {"appended": True, **result})
            except PermissionError as exc:
                self._send_error(403, 'HERMES_UNAUTHORIZED', str(exc))

        # ── Miner control routes ────────────────────────────────────────

        elif self.path == '/miner/start':
            result = miner.start()
            self._send_json(200 if result["success"] else 400, result)
        elif self.path == '/miner/stop':
            result = miner.stop()
            self._send_json(200 if result["success"] else 400, result)
        elif self.path == '/miner/set_mode':
            mode = data.get('mode')
            if not mode:
                self._send_error(400, 'MISSING_MODE', 'mode is required')
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
