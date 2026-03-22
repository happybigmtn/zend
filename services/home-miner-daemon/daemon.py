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
from dataclasses import asdict
from datetime import datetime, timezone
from enum import Enum
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from typing import Optional

# Import Hermes adapter
from hermes import (
    HermesConnection,
    HermesPairing,
    connect as hermes_connect,
    pair_hermes,
    read_status as hermes_read_status,
    append_summary as hermes_append_summary,
    get_filtered_events,
    list_hermes_pairings,
    validate_authority_token,
    require_capability,
    HERMES_CAPABILITIES,
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


# ---------------------------------------------------------------------------
# Hermes Authentication Helpers
# ---------------------------------------------------------------------------

def extract_hermes_auth(headers) -> Optional[str]:
    """
    Extract Hermes authority token from request headers.
    
    Expects: Authorization: Hermes <token>
    Returns: token string or None
    """
    auth_header = headers.get('Authorization', '')
    match = re.match(r'^Hermes\s+(.+)$', auth_header, re.IGNORECASE)
    if match:
        return match.group(1)
    return None


def require_hermes_auth(headers) -> HermesConnection:
    """
    Require valid Hermes auth and return the connection.
    
    Raises 401 if no valid auth header is present.
    """
    token = extract_hermes_auth(headers)
    if not token:
        raise ValueError("HERMES_AUTH_REQUIRED: Missing Hermes Authorization header")
    
    return hermes_connect(token)


def hermes_auth_or_none(headers) -> Optional[HermesConnection]:
    """
    Attempt to extract Hermes auth, return None if not present or invalid.
    
    Does NOT raise - returns None instead.
    """
    try:
        return require_hermes_auth(headers)
    except (ValueError, PermissionError):
        return None


# ---------------------------------------------------------------------------
# HTTP Request Handlers
# ---------------------------------------------------------------------------

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
        # Check if this is a Hermes request
        hermes_conn = hermes_auth_or_none(self.headers)
        
        if self.path == '/health':
            self._send_json(200, miner.health)
        elif self.path == '/status':
            self._send_json(200, miner.get_snapshot())
        # Hermes-specific endpoints
        elif self.path == '/hermes/status':
            self._handle_hermes_status(hermes_conn)
        elif self.path == '/hermes/events':
            self._handle_hermes_events(hermes_conn)
        elif self.path == '/hermes/pairings':
            self._handle_hermes_list_pairings()
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
            # Block Hermes from control commands
            if hermes_auth_or_none(self.headers):
                self._send_json(403, {
                    "error": "HERMES_UNAUTHORIZED",
                    "message": "Hermes agents cannot issue control commands"
                })
                return
            result = miner.start()
            self._send_json(200 if result["success"] else 400, result)
        elif self.path == '/miner/stop':
            # Block Hermes from control commands
            if hermes_auth_or_none(self.headers):
                self._send_json(403, {
                    "error": "HERMES_UNAUTHORIZED",
                    "message": "Hermes agents cannot issue control commands"
                })
                return
            result = miner.stop()
            self._send_json(200 if result["success"] else 400, result)
        elif self.path == '/miner/set_mode':
            # Block Hermes from control commands
            if hermes_auth_or_none(self.headers):
                self._send_json(403, {
                    "error": "HERMES_UNAUTHORIZED",
                    "message": "Hermes agents cannot issue control commands"
                })
                return
            mode = data.get('mode')
            if not mode:
                self._send_json(400, {"error": "missing_mode"})
                return
            result = miner.set_mode(mode)
            self._send_json(200 if result["success"] else 400, result)
        # Hermes-specific endpoints
        elif self.path == '/hermes/pair':
            self._handle_hermes_pair(data)
        elif self.path == '/hermes/connect':
            self._handle_hermes_connect(data)
        elif self.path == '/hermes/summary':
            self._handle_hermes_summary(self.headers, data)
        else:
            self._send_json(404, {"error": "not_found"})

    # ---------------------------------------------------------------------------
    # Hermes Endpoint Handlers
    # ---------------------------------------------------------------------------

    def _handle_hermes_pair(self, data: dict):
        """Handle Hermes pairing request."""
        hermes_id = data.get('hermes_id')
        device_name = data.get('device_name')
        
        if not hermes_id:
            self._send_json(400, {"error": "missing_hermes_id"})
            return
        if not device_name:
            device_name = f"hermes-{hermes_id}"
        
        try:
            pairing = pair_hermes(hermes_id, device_name, HERMES_CAPABILITIES)
            self._send_json(200, {
                "success": True,
                "hermes_id": pairing.hermes_id,
                "device_name": pairing.device_name,
                "capabilities": pairing.capabilities,
                "token": pairing.token,
                "paired_at": pairing.paired_at,
                "token_expires_at": pairing.token_expires_at
            })
        except ValueError as e:
            self._send_json(400, {"error": str(e)})

    def _handle_hermes_connect(self, data: dict):
        """Handle Hermes connection request."""
        token = data.get('authority_token')
        
        if not token:
            self._send_json(400, {"error": "missing_authority_token"})
            return
        
        try:
            conn = hermes_connect(token)
            self._send_json(200, {
                "success": True,
                "hermes_id": conn.hermes_id,
                "principal_id": conn.principal_id,
                "capabilities": conn.capabilities,
                "connected_at": conn.connected_at,
                "expires_at": conn.expires_at
            })
        except ValueError as e:
            self._send_json(401, {"error": str(e)})

    def _handle_hermes_status(self, hermes_conn: Optional[HermesConnection]):
        """Handle Hermes status read request."""
        if not hermes_conn:
            self._send_json(401, {"error": "HERMES_AUTH_REQUIRED"})
            return
        
        try:
            status = hermes_read_status(hermes_conn)
            self._send_json(200, {
                "success": True,
                "hermes_id": hermes_conn.hermes_id,
                "capabilities": hermes_conn.capabilities,
                "status": status
            })
        except PermissionError as e:
            self._send_json(403, {"error": str(e)})

    def _handle_hermes_summary(self, headers, data: dict):
        """Handle Hermes summary append request."""
        hermes_conn = hermes_auth_or_none(headers)
        if not hermes_conn:
            self._send_json(401, {"error": "HERMES_AUTH_REQUIRED"})
            return
        
        summary_text = data.get('summary_text')
        authority_scope = data.get('authority_scope', 'observe')
        
        if not summary_text:
            self._send_json(400, {"error": "missing_summary_text"})
            return
        
        try:
            event = hermes_append_summary(hermes_conn, summary_text, authority_scope)
            self._send_json(200, {
                "success": True,
                "appended": True,
                "event_id": event.id,
                "event_kind": event.kind,
                "created_at": event.created_at
            })
        except PermissionError as e:
            self._send_json(403, {"error": str(e)})

    def _handle_hermes_events(self, hermes_conn: Optional[HermesConnection]):
        """Handle Hermes filtered events request."""
        if not hermes_conn:
            self._send_json(401, {"error": "HERMES_AUTH_REQUIRED"})
            return
        
        events = get_filtered_events(hermes_conn, limit=20)
        self._send_json(200, {
            "success": True,
            "hermes_id": hermes_conn.hermes_id,
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

    def _handle_hermes_list_pairings(self):
        """Handle Hermes pairing list request (admin endpoint)."""
        pairings = list_hermes_pairings()
        self._send_json(200, {
            "success": True,
            "pairings": [
                {
                    "hermes_id": p.hermes_id,
                    "device_name": p.device_name,
                    "capabilities": p.capabilities,
                    "paired_at": p.paired_at,
                    "token_expires_at": p.token_expires_at
                }
                for p in pairings
            ]
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
