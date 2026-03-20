#!/usr/bin/env python3
"""
Tests for pairing store and capability enforcement.

These tests verify:
- Principal creation and loading
- Pairing record creation
- Capability checks for observe and control
- Duplicate device name rejection
"""

import json
import os
import uuid

import pytest


class TestPrincipalStore:
    """Tests for principal identity management."""

    def test_load_or_create_principal_creates_new(self, state_dir):
        """First call creates a new principal."""
        # Add tests package to path to import store module
        import sys
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

        # Set state dir for this test
        os.environ["ZEND_STATE_DIR"] = str(state_dir)

        from store import load_or_create_principal, PRINCIPAL_FILE

        principal = load_or_create_principal()

        assert principal.id is not None
        assert len(principal.id) == 36  # UUID format
        assert principal.name == "Zend Home"
        assert principal.created_at is not None
        assert os.path.exists(PRINCIPAL_FILE)

    def test_load_or_create_principal_loads_existing(self, state_dir):
        """Second call returns existing principal."""
        import sys
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

        os.environ["ZEND_STATE_DIR"] = str(state_dir)

        from store import load_or_create_principal

        first = load_or_create_principal()
        second = load_or_create_principal()

        assert first.id == second.id


class TestPairingStore:
    """Tests for gateway pairing records."""

    def test_pair_client_creates_record(self, state_dir):
        """pair_client creates a pairing record."""
        import sys
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

        os.environ["ZEND_STATE_DIR"] = str(state_dir)

        from store import load_or_create_principal, pair_client, get_pairing_by_device

        principal = load_or_create_principal()
        pairing = pair_client("test-device-1", ["observe", "control"])

        assert pairing.principal_id == principal.id
        assert pairing.device_name == "test-device-1"
        assert pairing.capabilities == ["observe", "control"]
        assert pairing.paired_at is not None
        assert pairing.token_used is False

    def test_pair_duplicate_device_rejected(self, state_dir):
        """Cannot pair same device name twice."""
        import sys
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

        os.environ["ZEND_STATE_DIR"] = str(state_dir)

        from store import pair_client

        pair_client("duplicate-test", ["observe"])

        with pytest.raises(ValueError, match="already paired"):
            pair_client("duplicate-test", ["observe"])

    def test_get_pairing_by_device(self, state_dir):
        """Can retrieve pairing by device name."""
        import sys
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

        os.environ["ZEND_STATE_DIR"] = str(state_dir)

        from store import pair_client, get_pairing_by_device

        created = pair_client("retrieve-test", ["observe"])

        retrieved = get_pairing_by_device("retrieve-test")

        assert retrieved is not None
        assert retrieved.id == created.id
        assert retrieved.device_name == "retrieve-test"


class TestCapabilityChecks:
    """Tests for capability enforcement."""

    def test_has_capability_observe(self, state_dir):
        """Device with observe capability returns True for observe check."""
        import sys
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

        os.environ["ZEND_STATE_DIR"] = str(state_dir)

        from store import pair_client, has_capability

        pair_client("capability-test", ["observe"])

        assert has_capability("capability-test", "observe") is True
        assert has_capability("capability-test", "control") is False

    def test_has_capability_control(self, state_dir):
        """Device with control capability returns True for control check."""
        import sys
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

        os.environ["ZEND_STATE_DIR"] = str(state_dir)

        from store import pair_client, has_capability

        pair_client("control-test", ["observe", "control"])

        assert has_capability("control-test", "observe") is True
        assert has_capability("control-test", "control") is True

    def test_has_capability_missing(self, state_dir):
        """Unpaired device returns False for all capability checks."""
        import sys
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

        os.environ["ZEND_STATE_DIR"] = str(state_dir)

        from store import has_capability

        assert has_capability("never-paired-device", "observe") is False
        assert has_capability("never-paired-device", "control") is False
