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
from typing import Optional, Tuple


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

# Active Hermes connections (in-memory for milestone 1)
# In production, this would use proper session management
_hermes_connections: dict[str, 'hermes.HermesConnection'] = {}


def _get_hermes_connection(handler: BaseHTTPRequestHandler) -> Tuple[Optional['hermes.HermesConnection'], Optional[dict]]:
    """
    Extract and validate Hermes connection from request headers.
    
    Returns:
        Tuple of (connection, error_response)
        If connection is valid, error_response is None
        If error, connection is None and error_response contains the error dict
    """
    # Import here to avoid circular imports
    from . import hermes
    
    # Get Authorization header
    auth_header = handler.headers.get('Authorization', '')
    
    # Expect format: "Hermes <hermes_id>"
    match = re.match(r'^Hermes\s+(\S+)$', auth_header)
    if not match:
        return None, {
            'error': 'HERMES_UNAUTHORIZED',
            'message': 'Missing or invalid Authorization header. Expected: Hermes <hermes_id>'
        }
    
    hermes_id = match.group(1)
    
    # Check for active connection
    if hermes_id not in _hermes_connections:
        return None, {
            'error': 'HERMES_UNAUTHORIZED',
            'message': f'No active connection for hermes_id: {hermes_id}. Use /hermes/connect first.'
        }
    
    return _hermes_connections[hermes_id], None


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
        # Import here to avoid circular imports
        from . import hermes
        
        # Health endpoint
        if self.path == '/health':
            self._send_json(200, miner.health)
        
        # Status endpoint
        elif self.path == '/status':
            self._send_json(200, miner.get_snapshot())
        
        # Hermes endpoints
        elif self.path == '/hermes/status':
            connection, error = _get_hermes_connection(self)
            if error:
                self._send_json(403, error)
                return
            try:
                status = hermes.read_status(connection)
                self._send_json(200, status)
            except PermissionError as e:
                self._send_json(403, {'error': 'HERMES_UNAUTHORIZED', 'message': str(e)})
        
        elif self.path == '/hermes/events':
            connection, error = _get_hermes_connection(self)
            if error:
                self._send_json(403, error)
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
            events = hermes.get_filtered_events(connection, limit)
            self._send_json(200, {
                'events': [
                    {
                        'id': e.id,
                        'kind': e.kind,
                        'payload': e.payload,
                        'created_at': e.created_at
                    }
                    for e in events
                ]
            })
        
        elif self.path == '/hermes/connection':
            # Return current Hermes connection state
            auth_header = self.headers.get('Authorization', '')
            match = re.match(r'^Hermes\s+(\S+)$', auth_header)
            if match:
                hermes_id = match.group(1)
                if hermes_id in _hermes_connections:
                    conn = _hermes_connections[hermes_id]
                    self._send_json(200, {
                        'connected': True,
                        'hermes_id': conn.hermes_id,
                        'capabilities': conn.capabilities,
                        'connected_at': conn.connected_at
                    })
                    return
            self._send_json(200, {
                'connected': False,
                'message': 'Use POST /hermes/connect to establish a connection'
            })
        
        else:
            self._send_json(404, {"error": "not_found"})

    def do_POST(self):
        # Import here to avoid circular imports
        from . import hermes
        
        content_length = int(self.headers.get('Content-Length', 0))
        body = self.rfile.read(content_length)

        try:
            data = json.loads(body) if body else {}
        except json.JSONDecodeError:
            self._send_json(400, {"error": "invalid_json"})
            return

        # Miner control endpoints
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
        
        # Hermes pairing endpoint
        elif self.path == '/hermes/pair':
            hermes_id = data.get('hermes_id')
            device_name = data.get('device_name', 'hermes-agent')
            if not hermes_id:
                self._send_json(400, {'error': 'missing_hermes_id', 'message': 'hermes_id is required'})
                return
            try:
                pairing = hermes.pair_hermes(hermes_id, device_name)
                token = hermes.get_pairing_token(hermes_id)
                self._send_json(200, {
                    'success': True,
                    'hermes_id': pairing.hermes_id,
                    'device_name': pairing.device_name,
                    'capabilities': pairing.capabilities,
                    'token': token,
                    'paired_at': pairing.paired_at
                })
            except ValueError as e:
                self._send_json(400, {'error': 'pairing_failed', 'message': str(e)})
        
        # Hermes connect endpoint
        elif self.path == '/hermes/connect':
            token = data.get('token')
            if not token:
                self._send_json(400, {'error': 'missing_token', 'message': 'token is required'})
                return
            try:
                connection = hermes.connect(token)
                # Store connection in memory
                _hermes_connections[connection.hermes_id] = connection
                self._send_json(200, {
                    'success': True,
                    'connected': True,
                    'hermes_id': connection.hermes_id,
                    'capabilities': connection.capabilities,
                    'connected_at': connection.connected_at
                })
            except ValueError as e:
                self._send_json(403, {'error': 'HERMES_UNAUTHORIZED', 'message': str(e)})
        
        # Hermes disconnect endpoint
        elif self.path == '/hermes/disconnect':
            auth_header = self.headers.get('Authorization', '')
            match = re.match(r'^Hermes\s+(\S+)$', auth_header)
            if match:
                hermes_id = match.group(1)
                if hermes_id in _hermes_connections:
                    del _hermes_connections[hermes_id]
                    self._send_json(200, {'success': True, 'disconnected': True})
                else:
                    self._send_json(200, {'success': True, 'disconnected': True, 'message': 'No active connection'})
            else:
                self._send_json(400, {'error': 'missing_hermes_id'})
        
        # Hermes summary endpoint
        elif self.path == '/hermes/summary':
            connection, error = _get_hermes_connection(self)
            if error:
                self._send_json(403, error)
                return
            summary_text = data.get('summary_text')
            authority_scope = data.get('authority_scope', 'observe')
            if not summary_text:
                self._send_json(400, {'error': 'missing_summary_text', 'message': 'summary_text is required'})
                return
            try:
                event = hermes.append_summary(connection, summary_text, authority_scope)
                self._send_json(200, {
                    'success': True,
                    'appended': True,
                    'event_id': event.id,
                    'kind': event.kind,
                    'created_at': event.created_at
                })
            except PermissionError as e:
                self._send_json(403, {'error': 'HERMES_UNAUTHORIZED', 'message': str(e)})
        
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
