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

import hermes as _hermes_adapter


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
    """HTTP handler for gateway API — includes Hermes adapter endpoints."""

    def log_message(self, format, *args):
        """Suppress default logging."""
        pass

    def _send_json(self, status: int, data: dict):
        self.send_response(status)
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps(data).encode())

    def _hermes_id_from_auth(self) -> Optional[str]:
        """Extract Hermes ID from Authorization header, or None if not Hermes auth."""
        return _hermes_adapter.is_hermes_authenticated(dict(self.headers))

    def _reject_hermes_control(self, path: str) -> bool:
        """
        Return True and send 403 if the request uses Hermes auth on a
        control endpoint. Blocks Hermes from issuing miner commands.
        """
        hermes_id = self._hermes_id_from_auth()
        if hermes_id:
            self._send_json(403, {
                "error": "HERMES_UNAUTHORIZED",
                "message": "Hermes does not have control capability",
                "action": path,
            })
            return True
        return False

    def do_GET(self):
        hermes_id = self._hermes_id_from_auth()

        if self.path == '/health':
            self._send_json(200, miner.health)

        elif self.path == '/status':
            self._send_json(200, miner.get_snapshot())

        # ---- Hermes adapter endpoints ----
        elif self.path == '/hermes/status':
            if not hermes_id:
                self._send_json(401, {"error": "HERMES_UNAUTHENTICATED"})
                return
            if not _hermes_adapter.check_hermes_capability(hermes_id, 'observe'):
                self._send_json(403, {"error": "HERMES_UNAUTHORIZED", "message": "observe capability required"})
                return
            # Build a connection object from stored pairing
            pairings = _hermes_adapter._load_hermes_pairings()
            record = pairings.get(hermes_id, {})
            conn = _hermes_adapter.HermesConnection(
                hermes_id=hermes_id,
                principal_id=record.get('principal_id', ''),
                capabilities=record.get('capabilities', []),
                connected_at=record.get('paired_at', ''),
            )
            status = _hermes_adapter.read_status(conn)
            self._send_json(200, {**status, "hermes_id": hermes_id})

        elif self.path == '/hermes/events':
            if not hermes_id:
                self._send_json(401, {"error": "HERMES_UNAUTHENTICATED"})
                return
            if not _hermes_adapter.check_hermes_capability(hermes_id, 'observe'):
                self._send_json(403, {"error": "HERMES_UNAUTHORIZED"})
                return
            pairings = _hermes_adapter._load_hermes_pairings()
            record = pairings.get(hermes_id, {})
            conn = _hermes_adapter.HermesConnection(
                hermes_id=hermes_id,
                principal_id=record.get('principal_id', ''),
                capabilities=record.get('capabilities', []),
                connected_at=record.get('paired_at', ''),
            )
            events = _hermes_adapter.get_filtered_events(conn)
            self._send_json(200, {
                "events": [
                    {
                        "id": e.id,
                        "kind": e.kind,
                        "payload": e.payload,
                        "created_at": e.created_at,
                    }
                    for e in events
                ]
            })

        else:
            self._send_json(404, {"error": "not_found"})

    def do_POST(self):
        # Block Hermes from control endpoints before processing
        control_paths = {'/miner/start', '/miner/stop', '/miner/set_mode'}
        if self.path in control_paths and self._reject_hermes_control(self.path):
            return

        content_length = int(self.headers.get('Content-Length', 0))
        body = self.rfile.read(content_length)

        try:
            data = json.loads(body) if body else {}
        except json.JSONDecodeError:
            self._send_json(400, {"error": "invalid_json"})
            return

        hermes_id = self._hermes_id_from_auth()

        # ---- Hermes adapter endpoints ----
        if self.path == '/hermes/connect':
            token = data.get('authority_token', '')
            if not token:
                self._send_json(400, {"error": "missing_authority_token"})
                return
            try:
                conn = _hermes_adapter.connect(token)
                self._send_json(200, conn.to_dict())
            except ValueError as e:
                self._send_json(401, {"error": str(e)})

        elif self.path == '/hermes/pair':
            hermes_id_req = data.get('hermes_id')
            device_name = data.get('device_name', 'hermes-agent')
            if not hermes_id_req:
                self._send_json(400, {"error": "missing_hermes_id"})
                return
            pairing = _hermes_adapter.pair(hermes_id=hermes_id_req, device_name=device_name)
            # Return the raw token so the caller can store it
            self._send_json(200, {
                "hermes_id": pairing.hermes_id,
                "device_name": pairing.device_name,
                "capabilities": pairing.capabilities,
                "paired_at": pairing.paired_at,
                "authority_token": pairing.token,
                "token_expires_at": pairing.token_expires_at,
            })

        elif self.path == '/hermes/summary':
            if not hermes_id:
                self._send_json(401, {"error": "HERMES_UNAUTHENTICATED"})
                return
            if not _hermes_adapter.check_hermes_capability(hermes_id, 'summarize'):
                self._send_json(403, {"error": "HERMES_UNAUTHORIZED", "message": "summarize capability required"})
                return
            summary_text = data.get('summary_text', '')
            authority_scope = data.get('authority_scope', 'observe')
            if not summary_text:
                self._send_json(400, {"error": "missing_summary_text"})
                return
            pairings = _hermes_adapter._load_hermes_pairings()
            record = pairings.get(hermes_id, {})
            conn = _hermes_adapter.HermesConnection(
                hermes_id=hermes_id,
                principal_id=record.get('principal_id', ''),
                capabilities=record.get('capabilities', []),
                connected_at=record.get('paired_at', ''),
            )
            event = _hermes_adapter.append_summary(conn, summary_text, authority_scope)
            self._send_json(200, {"appended": True, "event_id": event.id})

        # ---- Standard miner control ----
        elif self.path == '/miner/start':
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
    print("Press Ctrl+C to stop")

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down...")
        server.shutdown()


if __name__ == '__main__':
    run_server()
