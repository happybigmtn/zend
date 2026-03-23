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


# Hermes adapter (lazy import to avoid circular dependency)
def get_hermes_module():
    """Lazy import of hermes module."""
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent))
    import hermes
    return hermes


def extract_hermes_id(auth_header: str) -> Optional[str]:
    """Extract hermes_id from 'Hermes <hermes_id>' header."""
    if not auth_header:
        return None
    match = re.match(r'^Hermes\s+(.+)$', auth_header, re.IGNORECASE)
    return match.group(1) if match else None


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
        # Hermes endpoints
        if self.path == '/hermes/status':
            self._handle_hermes_status()
        elif self.path == '/hermes/events':
            self._handle_hermes_events()
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
            self._handle_hermes_connect(data)
        elif self.path == '/hermes/pair':
            self._handle_hermes_pair(data)
        elif self.path == '/hermes/summary':
            self._handle_hermes_summary(data)

        # Control endpoints (check Hermes auth)
        elif self.path == '/miner/start':
            self._handle_control_with_hermes_check(miner.start)
        elif self.path == '/miner/stop':
            self._handle_control_with_hermes_check(miner.stop)
        elif self.path == '/miner/set_mode':
            mode = data.get('mode')
            if not mode:
                self._send_json(400, {"error": "missing_mode"})
                return
            self._handle_control_with_hermes_check(
                lambda: miner.set_mode(mode)
            )
        else:
            self._send_json(404, {"error": "not_found"})

    def _handle_hermes_status(self):
        """GET /hermes/status - Read miner status through adapter."""
        hermes_id = extract_hermes_id(self.headers.get('Authorization', ''))
        if not hermes_id:
            self._send_json(401, {"error": "HERMES_UNAUTHORIZED", "message": "Missing Hermes authorization"})
            return

        try:
            hermes = get_hermes_module()
            connection = hermes.validate_hermes_auth(hermes_id)
            status = hermes.read_status(connection)
            self._send_json(200, status)
        except PermissionError as e:
            self._send_json(403, {"error": "HERMES_UNAUTHORIZED", "message": str(e)})
        except Exception as e:
            self._send_json(500, {"error": "internal_error", "message": str(e)})

    def _handle_hermes_events(self):
        """GET /hermes/events - Read filtered events (no user_message)."""
        hermes_id = extract_hermes_id(self.headers.get('Authorization', ''))
        if not hermes_id:
            self._send_json(401, {"error": "HERMES_UNAUTHORIZED", "message": "Missing Hermes authorization"})
            return

        try:
            hermes = get_hermes_module()
            connection = hermes.validate_hermes_auth(hermes_id)
            events = hermes.get_filtered_events(connection)
            self._send_json(200, {
                "events": [
                    {
                        "id": e.id,
                        "kind": e.kind,
                        "payload": e.payload,
                        "created_at": e.created_at
                    }
                    for e in events
                ]
            })
        except PermissionError as e:
            self._send_json(403, {"error": "HERMES_UNAUTHORIZED", "message": str(e)})
        except Exception as e:
            self._send_json(500, {"error": "internal_error", "message": str(e)})

    def _handle_hermes_connect(self, data: dict):
        """POST /hermes/connect - Accept authority token, return connection status."""
        authority_token = data.get('authority_token', '')
        if not authority_token:
            self._send_json(400, {"error": "missing_authority_token"})
            return

        try:
            hermes = get_hermes_module()
            connection = hermes.connect(authority_token)
            self._send_json(200, hermes.get_hermes_status(connection))
        except ValueError as e:
            self._send_json(401, {"error": "HERMES_INVALID_TOKEN", "message": str(e)})
        except Exception as e:
            self._send_json(500, {"error": "internal_error", "message": str(e)})

    def _handle_hermes_pair(self, data: dict):
        """POST /hermes/pair - Create Hermes pairing with observe+summarize capabilities."""
        hermes_id = data.get('hermes_id')
        device_name = data.get('device_name', 'hermes-agent')

        if not hermes_id:
            self._send_json(400, {"error": "missing_hermes_id"})
            return

        try:
            hermes = get_hermes_module()
            pairing = hermes.pair_hermes(hermes_id, device_name)
            self._send_json(200, {
                "hermes_id": pairing.hermes_id,
                "device_name": pairing.device_name,
                "capabilities": pairing.capabilities,
                "paired_at": pairing.paired_at,
                "token": pairing.token,
                "message": "Hermes paired successfully with observe + summarize capabilities"
            })
        except Exception as e:
            self._send_json(500, {"error": "internal_error", "message": str(e)})

    def _handle_hermes_summary(self, data: dict):
        """POST /hermes/summary - Append summary to event spine."""
        hermes_id = extract_hermes_id(self.headers.get('Authorization', ''))
        if not hermes_id:
            self._send_json(401, {"error": "HERMES_UNAUTHORIZED", "message": "Missing Hermes authorization"})
            return

        summary_text = data.get('summary_text')
        authority_scope = data.get('authority_scope', 'observe')

        if not summary_text:
            self._send_json(400, {"error": "missing_summary_text"})
            return

        try:
            hermes = get_hermes_module()
            connection = hermes.validate_hermes_auth(hermes_id)
            event = hermes.append_summary(connection, summary_text, authority_scope)
            self._send_json(200, {
                "appended": True,
                "event_id": event.id,
                "created_at": event.created_at
            })
        except PermissionError as e:
            self._send_json(403, {"error": "HERMES_UNAUTHORIZED", "message": str(e)})
        except Exception as e:
            self._send_json(500, {"error": "internal_error", "message": str(e)})

    def _handle_control_with_hermes_check(self, control_fn):
        """Execute control function if Hermes does not have authorization."""
        # Check if this is a Hermes-authenticated request
        hermes_id = extract_hermes_id(self.headers.get('Authorization', ''))
        if hermes_id:
            # Hermes is trying to issue a control command - BLOCK IT
            self._send_json(403, {
                "error": "HERMES_UNAUTHORIZED",
                "message": "Hermes does not have control capability. Only observe and summarize are allowed."
            })
            return

        # Not Hermes auth - execute control
        result = control_fn()
        self._send_json(200 if result["success"] else 400, result)

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
