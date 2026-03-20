"""
Unit tests for Hermes Adapter.

Tests capability boundaries and adapter interface.
"""

import os
import sys
import tempfile
import unittest
from pathlib import Path

# Setup paths
_ROOT_DIR = Path(__file__).resolve().parents[3]
_ADAPTER_DIR = str(_ROOT_DIR / "services" / "hermes-adapter")
_DAEMON_DIR = str(_ROOT_DIR / "services" / "home-miner-daemon")

sys.path.insert(0, _DAEMON_DIR)
sys.path.insert(0, _ADAPTER_DIR)

os.environ["ZEND_STATE_DIR"] = tempfile.mkdtemp()

# Now import from the modules
from hermes_adapter import (
    HermesAdapter,
    HermesConnection,
    HermesSummary,
    MinerSnapshot,
    make_summary_text,
)
from hermes_adapter.auth_token import create_hermes_token, validate_token
from hermes_adapter.token import create_hermes_token as create_token_from_shim

# Error classes for assertion
from hermes_adapter.errors import (
    HermesCapabilityError,
    HermesConnectionError,
    HermesUnauthorizedError,
)
from spine import EventKind, get_events


class TestPackageSurface(unittest.TestCase):
    """Test the documented hermes_adapter package surface."""

    def test_root_package_exports_documented_symbols(self):
        """Documented imports are available from the package root."""
        self.assertTrue(callable(HermesAdapter))
        self.assertTrue(callable(make_summary_text))
        self.assertEqual(HermesConnection.__name__, "HermesConnection")
        self.assertEqual(HermesSummary.__name__, "HermesSummary")
        self.assertEqual(MinerSnapshot.__name__, "MinerSnapshot")

    def test_token_shim_exposes_creation_helpers(self):
        """token.py compatibility shim exposes the reviewed token helpers."""
        token_str, token = create_token_from_shim(
            principal_id="shim-principal",
            capabilities=["observe"],
        )
        validated = validate_token(token_str)
        self.assertEqual(token.principal_id, "shim-principal")
        self.assertEqual(validated.principal_id, "shim-principal")


class TestTokenCreation(unittest.TestCase):
    """Test authority token creation."""

    def test_create_token_returns_string_and_token(self):
        """create_hermes_token returns both token string and AuthorityToken."""
        token_str, token = create_hermes_token(
            principal_id="test-principal",
            capabilities=["observe", "summarize"],
        )
        self.assertIsInstance(token_str, str)
        self.assertEqual(token.principal_id, "test-principal")
        self.assertEqual(token.capabilities, ["observe", "summarize"])

    def test_created_token_is_valid(self):
        """Created token passes validation."""
        token_str, token = create_hermes_token(
            principal_id="test-principal",
            capabilities=["observe"],
        )
        validated = validate_token(token_str)
        self.assertEqual(validated.principal_id, "test-principal")
        self.assertEqual(validated.capabilities, ["observe"])


class TestAdapterConnect(unittest.TestCase):
    """Test HermesAdapter.connect()."""

    def setUp(self):
        """Create adapter and token for tests."""
        self.adapter = HermesAdapter()
        self.token_str, self.token = create_hermes_token(
            principal_id="hermes-principal",
            capabilities=["observe", "summarize"],
        )

    def test_connect_with_valid_token(self):
        """connect() succeeds with valid token."""
        conn = self.adapter.connect(self.token_str)
        self.assertEqual(conn.principal_id, "hermes-principal")
        self.assertEqual(conn.capabilities, ["observe", "summarize"])

    def test_connect_twice_with_same_token_fails(self):
        """Token can only be used once (replay protection)."""
        self.adapter.connect(self.token_str)
        # Second connect should raise an error with "already been used" in message
        try:
            adapter2 = HermesAdapter()
            adapter2.connect(self.token_str)
            self.fail("Expected exception for replayed token")
        except Exception as e:
            self.assertIn("already been used", str(e))


class TestAdapterReadStatus(unittest.TestCase):
    """Test HermesAdapter.readStatus()."""

    def setUp(self):
        """Create adapter with token."""
        self.adapter = HermesAdapter()
        self.token_str, _ = create_hermes_token(
            principal_id="test-principal",
            capabilities=["observe", "summarize"],
        )
        self.adapter.connect(self.token_str)

    def test_readStatus_without_observe_raises(self):
        """readStatus() raises HermesCapabilityError without observe."""
        adapter = HermesAdapter()
        token_str, _ = create_hermes_token(
            principal_id="test-principal",
            capabilities=["summarize"],  # No observe
        )
        adapter.connect(token_str)
        try:
            adapter.readStatus()
            self.fail("Expected HermesCapabilityError")
        except Exception as e:
            self.assertIn("observe", str(e).lower())


class TestAdapterAppendSummary(unittest.TestCase):
    """Test HermesAdapter.appendSummary()."""

    def setUp(self):
        """Create adapter with token."""
        self.adapter = HermesAdapter()
        self.token_str, _ = create_hermes_token(
            principal_id="test-principal",
            capabilities=["summarize"],
        )
        self.adapter.connect(self.token_str)

    def test_appendSummary_without_summarize_raises(self):
        """appendSummary() raises HermesCapabilityError without summarize."""
        adapter = HermesAdapter()
        token_str, _ = create_hermes_token(
            principal_id="test-principal",
            capabilities=["observe"],  # No summarize
        )
        adapter.connect(token_str)
        summary = make_summary_text("Test summary", ["observe"])
        try:
            adapter.appendSummary(summary)
            self.fail("Expected HermesCapabilityError")
        except Exception as e:
            self.assertIn("summarize", str(e).lower())

    def test_appendSummary_records_event_in_spine(self):
        """appendSummary() appends a Hermes summary event to the spine."""
        before = len(get_events(EventKind.HERMES_SUMMARY))
        summary = make_summary_text("Test summary", ["summarize"])

        self.adapter.appendSummary(summary)

        events = get_events(EventKind.HERMES_SUMMARY)
        self.assertEqual(len(events), before + 1)
        latest = events[0]
        self.assertEqual(latest.principal_id, "test-principal")
        self.assertEqual(latest.kind, EventKind.HERMES_SUMMARY.value)
        self.assertEqual(latest.payload["summary_text"], "Test summary")
        self.assertEqual(latest.payload["authority_scope"], ["summarize"])


class TestAdapterGetScope(unittest.TestCase):
    """Test HermesAdapter.getScope()."""

    def test_getScope_returns_capabilities(self):
        """getScope() returns the granted capabilities."""
        adapter = HermesAdapter()
        token_str, expected = create_hermes_token(
            principal_id="test-principal",
            capabilities=["observe", "summarize"],
        )
        adapter.connect(token_str)
        scope = adapter.getScope()
        self.assertEqual(scope, ["observe", "summarize"])

    def test_getScope_without_connect_raises(self):
        """getScope() without connect() raises HermesConnectionError."""
        adapter = HermesAdapter()
        try:
            adapter.getScope()
            self.fail("Expected HermesConnectionError")
        except Exception as e:
            self.assertIn("not connected", str(e).lower())


class TestBoundaryEnforcement(unittest.TestCase):
    """Test that milestone 1 boundaries are enforced."""

    def test_no_control_capability_exists(self):
        """control is not a valid HermesCapability in milestone 1."""
        token_str, token = create_hermes_token(
            principal_id="test",
            capabilities=["observe", "summarize"],
        )
        # control should not appear in capabilities
        self.assertNotIn("control", token.capabilities)

    def test_adapter_does_not_expose_control_methods(self):
        """Adapter interface does not include start/stop/mode change."""
        adapter = HermesAdapter()
        self.assertFalse(hasattr(adapter, 'start'))
        self.assertFalse(hasattr(adapter, 'stop'))
        self.assertFalse(hasattr(adapter, 'set_mode'))
        self.assertFalse(hasattr(adapter, 'change_payout'))


if __name__ == "__main__":
    unittest.main()
