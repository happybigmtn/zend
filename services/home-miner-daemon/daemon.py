#!/usr/bin/env python3
"""
Zend Home Miner Daemon

LAN-only control service for milestone 1.
Binds to 127.0.0.1 only for local development/testing.
Production deployment uses the local network interface.

This is a milestone 1 simulator that exposes the same contract
a real miner backend will use.
"""

import socket
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

# Import spine and store for event spine and pairing records
import spine
import store


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

    def _check_capability(self, device_name: str, capability: str) -> bool:
        """Check if a device has the specified capability."""
        return store.has_capability(device_name, capability)

    def _get_client_device(self) -> Optional[str]:
        """Extract device name from Authorization header."""
        auth = self.headers.get('Authorization', '')
        if auth.startswith('Bearer '):
            return auth[7:]
        return None

    def _require_capability(self, capability: str) -> bool:
        """Check capability from Authorization header. Returns True if authorized."""
        device = self._get_client_device()
        if not device:
            self._send_json(401, {"error": "GATEWAY_UNAUTHORIZED", "message": "Missing or invalid Authorization header"})
            return False
        if not self._check_capability(device, capability):
            self._send_json(403, {"error": "GATEWAY_UNAUTHORIZED", "message": f"Device lacks '{capability}' capability"})
            return False
        return True

    def _inbox_destination(self, kind: str) -> str:
        """Route event kind to inbox destination per event-spine.md routing rules."""
        routes = {
            'pairing_requested': 'Device > Pairing',
            'pairing_granted': 'Device > Pairing',
            'capability_revoked': 'Device > Permissions',
            'miner_alert': 'Home,Inbox',
            'control_receipt': 'Inbox',
            'hermes_summary': 'Inbox,Agent',
            'user_message': 'Inbox',
        }
        return routes.get(kind, 'Inbox')

    def do_GET(self):
        if self.path == '/health':
            self._send_json(200, miner.health)
        elif self.path == '/status':
            self._send_json(200, miner.get_snapshot())
        elif self.path.startswith('/spine/events'):
            # Read events from the event spine
            if not self._require_capability('observe'):
                return
            # Parse query params for kind filter
            kind = None
            if '?' in self.path:
                import urllib.parse
                qs = urllib.parse.parse_qs(self.path.split('?', 1)[1])
                if 'kind' in qs:
                    kind = qs['kind'][0]
            # Load principal for filtering
            principal = store.load_or_create_principal()
            events = spine.get_events(kind=kind, limit=100) if kind else spine.get_events(limit=100)
            # Filter by principal_id
            filtered = [e for e in events if e.principal_id == principal.id]
            self._send_json(200, {"events": [
                {"id": e.id, "kind": e.kind, "payload": e.payload, "created_at": e.created_at}
                for e in filtered
            ]})
        elif self.path.startswith('/inbox'):
            # Derived inbox view of the event spine
            if not self._require_capability('observe'):
                return
            principal = store.load_or_create_principal()
            events = spine.get_events(limit=100)
            # Filter by principal and route to inbox based on kind
            filtered = [e for e in events if e.principal_id == principal.id]
            inbox_events = []
            for e in filtered:
                # Route based on event kind per event-spine.md routing rules
                if e.kind in ('pairing_requested', 'pairing_granted', 'capability_revoked',
                              'miner_alert', 'control_receipt', 'hermes_summary', 'user_message'):
                    inbox_events.append({
                        "id": e.id,
                        "kind": e.kind,
                        "payload": e.payload,
                        "created_at": e.created_at,
                        "destination": self._inbox_destination(e.kind)
                    })
            self._send_json(200, {"inbox": inbox_events})
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
            # Require control capability for start
            device = self._get_client_device()
            if device and not self._check_capability(device, 'control'):
                self._send_json(403, {"error": "GATEWAY_UNAUTHORIZED", "message": "Device lacks 'control' capability"})
                return
            result = miner.start()
            # Append control receipt to event spine
            if result.get("success"):
                principal = store.load_or_create_principal()
                spine.append_control_receipt('start', None, 'accepted', principal.id)
            self._send_json(200 if result["success"] else 400, result)
        elif self.path == '/miner/stop':
            # Require control capability for stop
            device = self._get_client_device()
            if device and not self._check_capability(device, 'control'):
                self._send_json(403, {"error": "GATEWAY_UNAUTHORIZED", "message": "Device lacks 'control' capability"})
                return
            result = miner.stop()
            # Append control receipt to event spine
            if result.get("success"):
                principal = store.load_or_create_principal()
                spine.append_control_receipt('stop', None, 'accepted', principal.id)
            self._send_json(200 if result["success"] else 400, result)
        elif self.path == '/miner/set_mode':
            # Require control capability for set_mode
            device = self._get_client_device()
            if device and not self._check_capability(device, 'control'):
                self._send_json(403, {"error": "GATEWAY_UNAUTHORIZED", "message": "Device lacks 'control' capability"})
                return
            mode = data.get('mode')
            if not mode:
                self._send_json(400, {"error": "missing_mode"})
                return
            result = miner.set_mode(mode)
            # Append control receipt to event spine
            if result.get("success"):
                principal = store.load_or_create_principal()
                spine.append_control_receipt('set_mode', mode, 'accepted', principal.id)
            self._send_json(200 if result["success"] else 400, result)
        else:
            self._send_json(404, {"error": "not_found"})


class ThreadedHTTPServer(socketserver.ThreadingMixIn, HTTPServer):
    """Threaded HTTP server for handling concurrent requests."""
    allow_reuse_address = True

    def server_bind(self):
        """Override server_bind to set SO_REUSEADDR before binding."""
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        super().server_bind()


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
