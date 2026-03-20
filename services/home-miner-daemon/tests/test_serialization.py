#!/usr/bin/env python3
"""
Tests for command serialization and conflict handling.

These tests verify:
- Conflicting commands are serialized (second command rejected)
- start_while_running returns already_running
- stop_while_stopped returns already_stopped
- Mode changes work correctly
- Hashrate updates based on mode
"""

import requests


class TestCommandSerialization:
    """Tests for serialized command handling."""

    def test_start_while_running_fails(self, daemon_url):
        """Second start while running returns already_running error."""
        # Ensure running
        requests.post(f"{daemon_url}/miner/stop")  # Reset to stopped
        requests.post(f"{daemon_url}/miner/start")  # Start

        # Second start should fail
        resp = requests.post(f"{daemon_url}/miner/start")
        data = resp.json()

        assert data["success"] is False
        assert data["error"] == "already_running"

    def test_stop_while_stopped_fails(self, daemon_url):
        """Second stop while stopped returns already_stopped error."""
        # Ensure stopped
        requests.post(f"{daemon_url}/miner/stop")

        # Second stop should fail
        resp = requests.post(f"{daemon_url}/miner/stop")
        data = resp.json()

        assert data["success"] is False
        assert data["error"] == "already_stopped"

    def test_mode_change_while_running(self, daemon_url):
        """Mode can change while miner is running."""
        # Start miner
        requests.post(f"{daemon_url}/miner/start")

        # Change to balanced
        resp = requests.post(
            f"{daemon_url}/miner/set_mode",
            json={"mode": "balanced"}
        )
        assert resp.json()["success"] is True

        # Change to performance
        resp = requests.post(
            f"{daemon_url}/miner/set_mode",
            json={"mode": "performance"}
        )
        assert resp.json()["success"] is True


class TestHashrateBehavior:
    """Tests for hashrate changes based on mode."""

    def test_mode_change_updates_hashrate(self, daemon_url):
        """Hashrate changes when mode changes."""
        # Start miner in balanced mode
        requests.post(f"{daemon_url}/miner/set_mode", json={"mode": "balanced"})
        requests.post(f"{daemon_url}/miner/start")

        # Check balanced hashrate
        resp = requests.get(f"{daemon_url}/status")
        balanced_hs = resp.json()["hashrate_hs"]

        # Change to performance
        requests.post(f"{daemon_url}/miner/set_mode", json={"mode": "performance"})

        # Check performance hashrate
        resp = requests.get(f"{daemon_url}/status")
        performance_hs = resp.json()["hashrate_hs"]

        assert balanced_hs > 0
        assert performance_hs > balanced_hs

    def test_paused_mode_zero_hashrate(self, daemon_url):
        """Paused mode results in zero hashrate."""
        # Set to paused and start
        requests.post(f"{daemon_url}/miner/set_mode", json={"mode": "paused"})
        requests.post(f"{daemon_url}/miner/start")

        resp = requests.get(f"{daemon_url}/status")
        assert resp.json()["hashrate_hs"] == 0
        assert resp.json()["mode"] == "paused"


class TestControlFlowEdgeCases:
    """Edge cases in control flow."""

    def test_start_after_stop_succeeds(self, daemon_url):
        """Can start again after stopping."""
        requests.post(f"{daemon_url}/miner/start")
        requests.post(f"{daemon_url}/miner/stop")

        resp = requests.post(f"{daemon_url}/miner/start")
        assert resp.json()["success"] is True

    def test_invalid_mode_rejected(self, daemon_url):
        """Invalid mode value is rejected."""
        resp = requests.post(
            f"{daemon_url}/miner/set_mode",
            json={"mode": "super_turbo"}
        )
        data = resp.json()
        assert data["success"] is False
        assert data["error"] == "invalid_mode"

    def test_status_reflects_current_state(self, daemon_url):
        """Status endpoint reflects current miner state."""
        # Ensure stopped first
        requests.post(f"{daemon_url}/miner/stop")

        # Verify stopped state
        resp = requests.get(f"{daemon_url}/status")
        assert resp.json()["status"] == "stopped"

        # After start
        requests.post(f"{daemon_url}/miner/start")
        resp = requests.get(f"{daemon_url}/status")
        assert resp.json()["status"] == "running"

        # After stop
        requests.post(f"{daemon_url}/miner/stop")
        resp = requests.get(f"{daemon_url}/status")
        assert resp.json()["status"] == "stopped"
