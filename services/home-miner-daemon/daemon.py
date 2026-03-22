#!/usr/bin/env python3
"""
Zend Home Miner Daemon

LAN-only control service for milestone 1.
Binds to 127.0.0.1 only for local development/testing.
Production deployment uses the local network interface.

This is a milestone 1 simulator that exposes the same contract
a real miner backend will use.

Hermes Integration:
    Hermes agents can connect through the Hermes adapter to observe miner
    status and append summaries to the event spine. They cannot issue control
    commands or read user messages.
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
from typing import Dict, Optional

# Hermes adapter integration
from hermes import (
    HermesConnection,
    HermesAuthError,
    HermesCapabilityError,
    pair_hermes,
    connect as hermes_connect,
    read_status as hermes_read_status,
    append_summary as hermes_append_summary,
    get_filtered_events as hermes_get_filtered_events,
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

# Active Hermes connections: hermes_id -> HermesConnection
active_hermes_connections: Dict[str, HermesConnection] = {}


def get_hermes_connection(hermes_id: str) -> Optional[HermesConnection]:
    """Get active Hermes connection by hermes_id."""
    return active_hermes_connections.get(hermes_id)


def store_hermes_connection(connection: HermesConnection) -> None:
    """Store an active Hermes connection."""
    active_hermes_connections[connection.hermes_id] = connection


def parse_hermes_auth_header(auth_header: str) -> tuple:
    """
    Parse Hermes Authorization header.
    
    Format: "Hermes <hermes_id>"
    
    Returns:
        Tuple of (scheme, hermes_id) or (None, None) if invalid
    """
    if not auth_header:
        return None, None
    
    parts = auth_header.split(' ', 1)
    if len(parts) != 2:
        return None, None
    
    return parts[0], parts[1]


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

    def _parse_body(self) -> Optional[dict]:
        """Parse JSON body from request. Can only be called once per request."""
        if hasattr(self, '_cached_body'):
            return self._cached_body
        
        content_length = int(self.headers.get('Content-Length', 0))
        body = self.rfile.read(content_length)
        try:
            self._cached_body = json.loads(body) if body else {}
            return self._cached_body
        except json.JSONDecodeError:
            self._cached_body = None
            return None

    def do_GET(self):
        # Hermes endpoints
        if self.path == '/hermes/status':
            self._handle_hermes_status()
        elif self.path == '/hermes/events':
            self._handle_hermes_events()
        elif self.path == '/hermes/connection':
            self._handle_hermes_connection_status()
        # Standard endpoints
        elif self.path == '/health':
            self._send_json(200, miner.health)
        elif self.path == '/status':
            self._send_json(200, miner.get_snapshot())
        else:
            self._send_json(404, {"error": "not_found"})

    def do_POST(self):
        # Check for Hermes attempting control commands
        auth_header = self.headers.get('Authorization', '')
        scheme, hermes_id = parse_hermes_auth_header(auth_header)
        
        if scheme == 'Hermes' and hermes_id:
            # Hermes control guard - Hermes cannot use control endpoints
            if self.path in ['/miner/start', '/miner/stop', '/miner/set_mode']:
                self._send_json(403, {
                    "error": "HERMES_UNAUTHORIZED",
                    "message": "Hermes agents cannot issue control commands",
                    "attempted_path": self.path
                })
                return
        
        # Parse body for all POST requests
        data = self._parse_body()
        if data is None:
            self._send_json(400, {"error": "invalid_json"})
            return
        
        # Hermes API endpoints
        if self.path == '/hermes/pair':
            self._handle_hermes_pair(data)
        elif self.path == '/hermes/connect':
            self._handle_hermes_connect(data)
        elif self.path == '/hermes/summary':
            self._handle_hermes_summary(data)
        # Standard miner control endpoints
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

    # ==================== Hermes Handlers ====================

    def _handle_hermes_pair(self, data: dict):
        """Handle Hermes pairing request."""
        hermes_id = data.get('hermes_id')
        device_name = data.get('device_name', f"hermes-{hermes_id}")
        
        if not hermes_id:
            self._send_json(400, {"error": "missing_hermes_id"})
            return
        
        try:
            pairing = pair_hermes(hermes_id, device_name)
            self._send_json(200, {
                "success": True,
                "hermes_id": pairing.hermes_id,
                "device_name": pairing.device_name,
                "capabilities": pairing.capabilities,
                "paired_at": pairing.paired_at,
                "token_expires_at": pairing.token_expires_at
            })
        except Exception as e:
            self._send_json(500, {"error": "pairing_failed", "details": str(e)})

    def _handle_hermes_connect(self, data: dict):
        """Handle Hermes connection establishment."""
        authority_token = data.get('authority_token', '')
        hermes_id = data.get('hermes_id')
        
        if not hermes_id:
            self._send_json(400, {"error": "missing_hermes_id"})
            return
        
        try:
            connection = hermes_connect(authority_token, hermes_id)
            store_hermes_connection(connection)
            self._send_json(200, {
                "connected": True,
                "hermes_id": connection.hermes_id,
                "principal_id": connection.principal_id,
                "capabilities": connection.capabilities,
                "connected_at": connection.connected_at
            })
        except HermesAuthError as e:
            self._send_json(401, {"error": "HERMES_AUTH_FAILED", "message": str(e)})
        except Exception as e:
            self._send_json(500, {"error": "connection_failed", "details": str(e)})

    def _handle_hermes_status(self):
        """Handle Hermes status read request."""
        auth_header = self.headers.get('Authorization', '')
        scheme, hermes_id = parse_hermes_auth_header(auth_header)
        
        if scheme != 'Hermes' or not hermes_id:
            self._send_json(401, {"error": "missing_hermes_auth"})
            return
        
        connection = get_hermes_connection(hermes_id)
        if not connection:
            self._send_json(401, {"error": "hermes_not_connected"})
            return
        
        try:
            status = hermes_read_status(connection)
            self._send_json(200, {
                "hermes_id": hermes_id,
                "status": status
            })
        except HermesCapabilityError as e:
            self._send_json(403, {"error": "HERMES_UNAUTHORIZED", "message": str(e)})
        except Exception as e:
            self._send_json(500, {"error": "status_read_failed", "details": str(e)})

    def _handle_hermes_summary(self, data: dict):
        """Handle Hermes summary append request."""
        auth_header = self.headers.get('Authorization', '')
        scheme, hermes_id = parse_hermes_auth_header(auth_header)
        
        if scheme != 'Hermes' or not hermes_id:
            self._send_json(401, {"error": "missing_hermes_auth"})
            return
        
        connection = get_hermes_connection(hermes_id)
        if not connection:
            self._send_json(401, {"error": "hermes_not_connected"})
            return
        
        summary_text = data.get('summary_text')
        authority_scope = data.get('authority_scope', 'observe')
        
        if not summary_text:
            self._send_json(400, {"error": "missing_summary_text"})
            return
        
        try:
            result = hermes_append_summary(connection, summary_text, authority_scope)
            self._send_json(200, result)
        except HermesCapabilityError as e:
            self._send_json(403, {"error": "HERMES_UNAUTHORIZED", "message": str(e)})
        except Exception as e:
            self._send_json(500, {"error": "summary_append_failed", "details": str(e)})

    def _handle_hermes_events(self):
        """Handle Hermes filtered events request."""
        auth_header = self.headers.get('Authorization', '')
        scheme, hermes_id = parse_hermes_auth_header(auth_header)
        
        if scheme != 'Hermes' or not hermes_id:
            self._send_json(401, {"error": "missing_hermes_auth"})
            return
        
        connection = get_hermes_connection(hermes_id)
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
            events = hermes_get_filtered_events(connection, limit=limit)
            self._send_json(200, {
                "hermes_id": hermes_id,
                "events": events,
                "count": len(events)
            })
        except Exception as e:
            self._send_json(500, {"error": "events_read_failed", "details": str(e)})

    def _handle_hermes_connection_status(self):
        """Handle Hermes connection status request."""
        auth_header = self.headers.get('Authorization', '')
        scheme, hermes_id = parse_hermes_auth_header(auth_header)
        
        if scheme != 'Hermes' or not hermes_id:
            self._send_json(401, {"error": "missing_hermes_auth"})
            return
        
        connection = get_hermes_connection(hermes_id)
        if not connection:
            self._send_json(200, {
                "hermes_id": hermes_id,
                "connected": False,
                "capabilities": []
            })
            return
        
        self._send_json(200, {
            "hermes_id": hermes_id,
            "connected": True,
            "principal_id": connection.principal_id,
            "capabilities": connection.capabilities,
            "connected_at": connection.connected_at
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
