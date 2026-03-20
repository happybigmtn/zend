#!/usr/bin/env python3
"""
Tests for daemon HTTP endpoints.

These tests verify the daemon's HTTP API surface:
- /health — returns daemon health
- /status — returns miner snapshot
- /miner/start — starts mining
- /miner/stop — stops mining
- /miner/set_mode — changes mode
"""

import json

import pytest
import requests


class TestHealthEndpoint:
    """Tests for GET /health."""

    def test_health_returns_valid_response(self, daemon_url):
        """GET /health returns healthy, temperature, and uptime."""
        resp = requests.get(f"{daemon_url}/health")
        assert resp.status_code == 200

        data = resp.json()
        assert "healthy" in data
        assert "temperature" in data
        assert "uptime_seconds" in data
        assert isinstance(data["healthy"], bool)
        assert isinstance(data["temperature"], (int, float))
        assert isinstance(data["uptime_seconds"], int)

    def test_health_content_type(self, daemon_url):
        """GET /health returns application/json."""
        resp = requests.get(f"{daemon_url}/health")
        assert resp.headers.get("Content-Type") == "application/json"


class TestStatusEndpoint:
    """Tests for GET /status."""

    def test_status_returns_fresh_snapshot(self, daemon_url):
        """GET /status returns a MinerSnapshot with freshness timestamp."""
        resp = requests.get(f"{daemon_url}/status")
        assert resp.status_code == 200

        data = resp.json()
        assert "status" in data
        assert "mode" in data
        assert "hashrate_hs" in data
        assert "temperature" in data
        assert "uptime_seconds" in data
        assert "freshness" in data

        # Freshness must be ISO format
        assert "T" in data["freshness"]  # ISO timestamp contains 'T'

    def test_status_values_are_valid(self, daemon_url):
        """Status values are from the expected enums."""
        resp = requests.get(f"{daemon_url}/status")
        data = resp.json()

        # Status must be a known MinerStatus
        assert data["status"] in ("running", "stopped", "offline", "error")
        # Mode must be a known MinerMode
        assert data["mode"] in ("paused", "balanced", "performance")
        # Hashrate must be non-negative
        assert data["hashrate_hs"] >= 0


class TestMinerEndpoints:
    """Tests for POST /miner/* endpoints."""

    def test_miner_start_succeeds_when_stopped(self, daemon_url):
        """POST /miner/start returns success when miner is stopped."""
        # Ensure miner is stopped first
        requests.post(f"{daemon_url}/miner/stop")

        resp = requests.post(f"{daemon_url}/miner/start")
        assert resp.status_code == 200

        data = resp.json()
        assert data["success"] is True
        assert data["status"] == "running"

    def test_miner_start_already_running(self, daemon_url):
        """POST /miner/start returns error when already running."""
        # Ensure miner is running
        requests.post(f"{daemon_url}/miner/start")

        resp = requests.post(f"{daemon_url}/miner/start")
        # Returns 200 but success=false (current implementation)
        data = resp.json()
        assert data["success"] is False
        assert data["error"] == "already_running"

    def test_miner_stop_succeeds_when_running(self, daemon_url):
        """POST /miner/stop returns success when miner is running."""
        # Ensure miner is running
        requests.post(f"{daemon_url}/miner/start")

        resp = requests.post(f"{daemon_url}/miner/stop")
        assert resp.status_code == 200

        data = resp.json()
        assert data["success"] is True
        assert data["status"] == "stopped"

    def test_miner_stop_already_stopped(self, daemon_url):
        """POST /miner/stop returns error when already stopped."""
        # Ensure miner is stopped
        requests.post(f"{daemon_url}/miner/stop")

        resp = requests.post(f"{daemon_url}/miner/stop")
        data = resp.json()
        assert data["success"] is False
        assert data["error"] == "already_stopped"

    def test_miner_set_mode_valid(self, daemon_url):
        """POST /miner/set_mode with valid mode succeeds."""
        resp = requests.post(
            f"{daemon_url}/miner/set_mode",
            json={"mode": "balanced"}
        )
        assert resp.status_code == 200

        data = resp.json()
        assert data["success"] is True
        assert data["mode"] == "balanced"

    def test_miner_set_mode_invalid(self, daemon_url):
        """POST /miner/set_mode with invalid mode returns error."""
        resp = requests.post(
            f"{daemon_url}/miner/set_mode",
            json={"mode": "turbo"}  # Not a valid mode
        )
        # Returns 200 but success=false
        data = resp.json()
        assert data["success"] is False
        assert data["error"] == "invalid_mode"

    def test_miner_set_mode_missing_mode(self, daemon_url):
        """POST /miner/set_mode without mode returns error."""
        resp = requests.post(
            f"{daemon_url}/miner/set_mode",
            json={}
        )
        assert resp.status_code == 400
        data = resp.json()
        assert data["error"] == "missing_mode"


class TestUnknownEndpoints:
    """Tests for unknown endpoints."""

    def test_unknown_endpoint_returns_404(self, daemon_url):
        """Unknown paths return 404."""
        resp = requests.get(f"{daemon_url}/nonexistent")
        assert resp.status_code == 404
        data = resp.json()
        assert data["error"] == "not_found"

    def test_invalid_json_returns_error(self, daemon_url):
        """POST with invalid JSON returns error."""
        resp = requests.post(
            f"{daemon_url}/miner/start",
            data="not json",
            headers={"Content-Type": "application/json"}
        )
        assert resp.status_code == 400
        data = resp.json()
        assert data["error"] == "invalid_json"
