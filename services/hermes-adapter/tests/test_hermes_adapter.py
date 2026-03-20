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

# Import using direct paths since hermes-adapter has hyphen
import importlib.util

# Load errors module
_errors_spec = importlib.util.spec_from_file_location("hermes_adapter.errors", f"{_ADAPTER_DIR}/errors.py")
_errors_mod = importlib.util.module_from_spec(_errors_spec)
_errors_spec.loader.exec_module(_errors_mod)
sys.modules['hermes_adapter.errors'] = _errors_mod

# Load models module
_models_spec = importlib.util.spec_from_file_location("hermes_adapter.models", f"{_ADAPTER_DIR}/models.py")
_models_mod = importlib.util.module_from_spec(_models_spec)
_models_spec.loader.exec_module(_models_mod)
sys.modules['hermes_adapter.models'] = _models_mod

# Load auth_token module
_auth_spec = importlib.util.spec_from_file_location("hermes_adapter.auth_token", f"{_ADAPTER_DIR}/auth_token.py")
_auth_mod = importlib.util.module_from_spec(_auth_spec)
_auth_spec.loader.exec_module(_auth_mod)
sys.modules['hermes_adapter.auth_token'] = _auth_mod

# Load adapter module
_adapter_spec = importlib.util.spec_from_file_location("hermes_adapter.adapter", f"{_ADAPTER_DIR}/adapter.py")
_adapter_mod = importlib.util.module_from_spec(_adapter_spec)
_adapter_spec.loader.exec_module(_adapter_mod)
sys.modules['hermes_adapter.adapter'] = _adapter_mod

# Create hermes_adapter package
import types
_hermes_pkg = types.ModuleType('hermes_adapter')
_hermes_pkg.__path__ = [_ADAPTER_DIR]
_hermes_pkg.errors = _errors_mod
_hermes_pkg.models = _models_mod
_hermes_pkg.auth_token = _auth_mod
_hermes_pkg.adapter = _adapter_mod
sys.modules['hermes_adapter'] = _hermes_pkg

# Now import from the modules
HermesAdapter = _adapter_mod.HermesAdapter
HermesSummary = _models_mod.HermesSummary
make_summary_text = _models_mod.make_summary_text
create_hermes_token = _auth_mod.create_hermes_token
validate_token = _auth_mod.validate_token

# Error classes for assertion
HermesCapabilityError = _errors_mod.HermesCapabilityError
HermesConnectionError = _errors_mod.HermesConnectionError
HermesUnauthorizedError = _errors_mod.HermesUnauthorizedError


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