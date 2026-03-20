#!/usr/bin/env python3
"""
Unit tests for Hermes Adapter.

Tests the HermesAdapter class with various capability combinations
and error conditions.
"""

import json
import importlib
import os
import subprocess
import tempfile
import unittest
from datetime import datetime, timezone, timedelta
from pathlib import Path

# Ensure the module is importable
import sys
_test_dir = Path(__file__).resolve().parents[0]
sys.path.insert(0, str(_test_dir))

import adapter
from adapter import (
    HermesAdapter,
    HermesAdapterError,
    InvalidTokenError,
    ExpiredTokenError,
    UnauthorizedError,
    HermesCapability,
    create_hermes_token,
)


class TestHermesAdapter(unittest.TestCase):
    """Test cases for HermesAdapter."""

    def setUp(self):
        """Create a temporary state directory for each test."""
        self.temp_dir = tempfile.mkdtemp()
        os.environ['ZEND_STATE_DIR'] = self.temp_dir
        self.adapter = HermesAdapter(state_dir=self.temp_dir)

    def tearDown(self):
        """Clean up temporary state."""
        import shutil
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)

    def test_create_token(self):
        """Test token creation returns valid token."""
        principal_id = "test-principal-123"
        capabilities = ["observe", "summarize"]

        token, encoded = create_hermes_token(
            principal_id=principal_id,
            capabilities=capabilities
        )

        self.assertIsInstance(token, str)
        self.assertTrue(len(token) > 0)
        self.assertIsInstance(encoded, str)

    def test_connect_with_valid_token(self):
        """Test connecting with a valid token."""
        principal_id = "test-principal-123"
        capabilities = ["observe", "summarize"]

        token, _ = create_hermes_token(
            principal_id=principal_id,
            capabilities=capabilities
        )

        connection = self.adapter.connect(token)

        self.assertEqual(connection.claims.principal_id, principal_id)
        self.assertEqual(connection.claims.capabilities, capabilities)
        self.assertIsNotNone(connection.connection_id)

    def test_connect_with_expired_token(self):
        """Test connecting with an expired token raises error."""
        principal_id = "test-principal-123"
        capabilities = ["observe"]

        # Create a token that expired yesterday
        expired_time = (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()
        token, _ = create_hermes_token(
            principal_id=principal_id,
            capabilities=capabilities,
            expires_at=expired_time
        )

        with self.assertRaises(ExpiredTokenError):
            self.adapter.connect(token)

    def test_connect_with_invalid_token(self):
        """Test connecting with an invalid token raises error."""
        with self.assertRaises(InvalidTokenError):
            self.adapter.connect("not-a-valid-token")

    def test_get_scope(self):
        """Test getting connection scope."""
        principal_id = "test-principal-123"
        capabilities = ["observe", "summarize"]

        token, _ = create_hermes_token(
            principal_id=principal_id,
            capabilities=capabilities
        )

        connection = self.adapter.connect(token)
        scope = self.adapter.get_scope(connection)

        self.assertEqual(scope, capabilities)

    def test_read_status_requires_observe(self):
        """Test read_status requires observe capability."""
        principal_id = "test-principal-123"
        # Only summarize capability, no observe
        capabilities = ["summarize"]

        token, _ = create_hermes_token(
            principal_id=principal_id,
            capabilities=capabilities
        )

        connection = self.adapter.connect(token)

        with self.assertRaises(UnauthorizedError) as ctx:
            self.adapter.read_status(connection)

        self.assertIn("observe", str(ctx.exception))

    def test_append_summary_requires_summarize(self):
        """Test append_summary requires summarize capability."""
        principal_id = "test-principal-123"
        # Only observe capability, no summarize
        capabilities = ["observe"]

        token, _ = create_hermes_token(
            principal_id=principal_id,
            capabilities=capabilities
        )

        connection = self.adapter.connect(token)

        with self.assertRaises(UnauthorizedError) as ctx:
            self.adapter.append_summary(connection, "Test summary")

        self.assertIn("summarize", str(ctx.exception))

    def test_append_summary_success(self):
        """Test successful summary append."""
        principal_id = "test-principal-123"
        capabilities = ["summarize"]

        token, _ = create_hermes_token(
            principal_id=principal_id,
            capabilities=capabilities
        )

        connection = self.adapter.connect(token)
        event = self.adapter.append_summary(connection, "Miner running well")

        self.assertIsNotNone(event)
        self.assertEqual(event.kind, "hermes_summary")
        self.assertEqual(event.principal_id, principal_id)
        self.assertEqual(event.payload["summary_text"], "Miner running well")

    def test_disconnect(self):
        """Test disconnecting a connection."""
        principal_id = "test-principal-123"
        capabilities = ["observe"]

        token, _ = create_hermes_token(
            principal_id=principal_id,
            capabilities=capabilities
        )

        connection = self.adapter.connect(token)
        connection_id = connection.connection_id

        # Connection should exist
        self.assertIsNotNone(self.adapter.get_connection(connection_id))

        # Disconnect
        result = self.adapter.disconnect(connection_id)
        self.assertTrue(result)

        # Connection should no longer exist
        self.assertIsNone(self.adapter.get_connection(connection_id))

    def test_disconnect_nonexistent(self):
        """Test disconnecting a nonexistent connection returns False."""
        result = self.adapter.disconnect("nonexistent-id")
        self.assertFalse(result)

    def test_get_connection_not_found(self):
        """Test getting a nonexistent connection returns None."""
        result = self.adapter.get_connection("nonexistent-id")
        self.assertIsNone(result)


class TestTokenClaims(unittest.TestCase):
    """Test cases for TokenClaims parsing."""

    def setUp(self):
        """Create a temporary state directory for each test."""
        self.temp_dir = tempfile.mkdtemp()
        os.environ['ZEND_STATE_DIR'] = self.temp_dir

    def tearDown(self):
        """Clean up temporary state."""
        import shutil
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)

    def test_token_persistence(self):
        """Test tokens are persisted and can be retrieved."""
        from adapter import TokenClaims
        import adapter as adapter_module

        principal_id = "test-principal-456"
        capabilities = ["observe", "summarize"]
        expires_at = (datetime.now(timezone.utc) + timedelta(hours=24)).isoformat()

        # Ensure we're using the correct temp_dir
        adapter_module.STATE_DIR = None
        os.environ['ZEND_STATE_DIR'] = self.temp_dir

        token1, _ = create_hermes_token(
            principal_id=principal_id,
            capabilities=capabilities,
            expires_at=expires_at
        )

        # Create a new adapter instance (simulating restart)
        adapter_module.STATE_DIR = None
        adapter2 = HermesAdapter(state_dir=self.temp_dir)

        # Should be able to connect with same token
        connection = adapter2.connect(token1)
        self.assertEqual(connection.claims.principal_id, principal_id)


class TestHermesCapability(unittest.TestCase):
    """Test cases for HermesCapability enum."""

    def test_capability_values(self):
        """Test capability enum values."""
        self.assertEqual(HermesCapability.OBSERVE.value, "observe")
        self.assertEqual(HermesCapability.SUMMARIZE.value, "summarize")

    def test_capability_from_string(self):
        """Test creating capability from string."""
        observe = HermesCapability("observe")
        self.assertEqual(observe, HermesCapability.OBSERVE)


class FakeGatewayHandler:
    """Minimal handler double for testing JSON responses without sockets."""

    def __init__(self, path: str, headers: dict | None = None):
        self.path = path
        self.headers = headers or {}
        self.responses: list[tuple[int, dict]] = []

    def _send_json(self, status: int, data: dict):
        self.responses.append((status, data))


class TestHermesGatewayHandler(unittest.TestCase):
    """Endpoint-level Hermes handler tests without binding a real socket."""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        os.environ['ZEND_STATE_DIR'] = self.temp_dir
        adapter.STATE_DIR = None
        self.daemon = importlib.reload(importlib.import_module("daemon"))
        self.daemon.hermes_adapter = HermesAdapter(state_dir=self.temp_dir)

    def tearDown(self):
        import shutil
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)

    def test_hermes_connect_missing_authority_token_returns_400(self):
        handler = FakeGatewayHandler("/hermes/connect")

        self.daemon.GatewayHandler._handle_hermes_connect(handler, {})

        self.assertEqual(handler.responses, [
            (400, {"error": "missing_authority_token"})
        ])

    def test_hermes_connect_success_returns_connection_payload(self):
        token, _ = create_hermes_token(
            principal_id="test-principal-123",
            capabilities=["observe", "summarize"]
        )
        handler = FakeGatewayHandler("/hermes/connect")

        self.daemon.GatewayHandler._handle_hermes_connect(
            handler,
            {"authority_token": token}
        )

        status, payload = handler.responses[0]
        self.assertEqual(status, 200)
        self.assertEqual(payload["principal_id"], "test-principal-123")
        self.assertEqual(payload["capabilities"], ["observe", "summarize"])
        self.assertIn("connection_id", payload)

    def test_hermes_status_requires_connection_id_header(self):
        handler = FakeGatewayHandler("/hermes/status")

        self.daemon.GatewayHandler._handle_hermes_get(handler)

        self.assertEqual(handler.responses, [
            (400, {"error": "missing_connection_id"})
        ])

    def test_hermes_status_returns_404_for_unknown_connection(self):
        handler = FakeGatewayHandler(
            "/hermes/status",
            headers={"X-Connection-ID": "missing"}
        )

        self.daemon.GatewayHandler._handle_hermes_get(handler)

        self.assertEqual(handler.responses, [
            (404, {"error": "connection_not_found"})
        ])

    def test_hermes_status_maps_unauthorized_error_to_403(self):
        token, _ = create_hermes_token(
            principal_id="test-principal-123",
            capabilities=["summarize"]
        )
        connection = self.daemon.hermes_adapter.connect(token)
        handler = FakeGatewayHandler(
            "/hermes/status",
            headers={"X-Connection-ID": connection.connection_id}
        )

        self.daemon.GatewayHandler._handle_hermes_get(handler)

        status, payload = handler.responses[0]
        self.assertEqual(status, 403)
        self.assertEqual(payload["error"], "unauthorized")
        self.assertIn("observe", payload["message"])

    def test_hermes_summary_missing_text_returns_400(self):
        handler = FakeGatewayHandler("/hermes/summary")

        self.daemon.GatewayHandler._handle_hermes_summary(
            handler,
            {"connection_id": "test-connection"}
        )

        self.assertEqual(handler.responses, [
            (400, {"error": "missing_summary_text"})
        ])


class TestHermesBootstrapScript(unittest.TestCase):
    """Bootstrap script tests for deterministic Hermes daemon failure handling."""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.repo_root = Path(__file__).resolve().parents[2]
        self.script = self.repo_root / "scripts" / "bootstrap_hermes.sh"

    def tearDown(self):
        import shutil
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)

    def test_bootstrap_hermes_reports_gateway_unavailable_when_daemon_exits(self):
        env = os.environ.copy()
        env["ZEND_STATE_DIR"] = self.temp_dir
        env["ZEND_DAEMON_PYTHON"] = "false"
        env["ZEND_STARTUP_RETRIES"] = "1"
        env["ZEND_STARTUP_INTERVAL_SECONDS"] = "0"

        result = subprocess.run(
            [str(self.script), "--daemon"],
            cwd=self.repo_root,
            env=env,
            text=True,
            capture_output=True,
            check=False,
        )

        combined_output = f"{result.stdout}\n{result.stderr}"
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("error_code=GATEWAY_UNAVAILABLE", combined_output)
        self.assertIn("reason=daemon_process_exited", combined_output)
        self.assertFalse(Path(self.temp_dir, "daemon.pid").exists())


if __name__ == '__main__':
    unittest.main()
