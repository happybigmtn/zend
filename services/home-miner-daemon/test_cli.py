#!/usr/bin/env python3
"""
Targeted CLI tests for the command-center-client lane.

These tests exercise the smallest approved slice called out in the reviewed
lane artifacts: bootstrap, pairing, capability enforcement, and control
receipt append.
"""

import argparse
import importlib
import io
import json
import os
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest import mock


SERVICE_DIR = Path(__file__).resolve().parent
if str(SERVICE_DIR) not in sys.path:
    sys.path.insert(0, str(SERVICE_DIR))


class CLITestCase(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.state_dir = self.temp_dir.name
        self.original_env = {
            "ZEND_STATE_DIR": os.environ.get("ZEND_STATE_DIR"),
            "ZEND_DAEMON_URL": os.environ.get("ZEND_DAEMON_URL"),
        }

        os.environ["ZEND_STATE_DIR"] = self.state_dir
        os.environ["ZEND_DAEMON_URL"] = "http://127.0.0.1:65535"

        self.store, self.spine, self.cli = self._reload_modules()

    def tearDown(self):
        for key, value in self.original_env.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value

        for module_name in ("cli", "spine", "store"):
            sys.modules.pop(module_name, None)

        self.temp_dir.cleanup()

    def _reload_modules(self):
        importlib.invalidate_caches()
        for module_name in ("cli", "spine", "store"):
            sys.modules.pop(module_name, None)

        import store
        import spine
        import cli

        return store, spine, cli

    def _run_command(self, fn, args):
        output = io.StringIO()
        with redirect_stdout(output):
            exit_code = fn(args)
        return exit_code, output.getvalue().strip()

    def test_bootstrap_creates_principal_pairing_and_event(self):
        exit_code, stdout = self._run_command(
            self.cli.cmd_bootstrap,
            argparse.Namespace(device="alice-phone"),
        )

        self.assertEqual(exit_code, 0)

        payload = json.loads(stdout)
        self.assertEqual(payload["device_name"], "alice-phone")
        self.assertEqual(payload["capabilities"], ["observe"])

        principal_path = Path(self.state_dir) / "principal.json"
        pairing_path = Path(self.state_dir) / "pairing-store.json"
        self.assertTrue(principal_path.exists())
        self.assertTrue(pairing_path.exists())

        principal = json.loads(principal_path.read_text())
        pairings = json.loads(pairing_path.read_text())
        self.assertEqual(principal["id"], payload["principal_id"])
        self.assertEqual(len(pairings), 1)

        events = self.spine.get_events()
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0].kind, self.spine.EventKind.PAIRING_GRANTED.value)
        self.assertEqual(events[0].payload["device_name"], "alice-phone")

    def test_pair_command_records_pairing_and_rejects_duplicate_device_names(self):
        pair_args = argparse.Namespace(device="guest-phone", capabilities="observe,control")

        exit_code, stdout = self._run_command(self.cli.cmd_pair, pair_args)
        self.assertEqual(exit_code, 0)

        payload = json.loads(stdout)
        self.assertTrue(payload["success"])
        self.assertEqual(payload["device_name"], "guest-phone")
        self.assertEqual(payload["capabilities"], ["observe", "control"])

        exit_code, stdout = self._run_command(self.cli.cmd_pair, pair_args)
        self.assertEqual(exit_code, 1)

        payload = json.loads(stdout)
        self.assertFalse(payload["success"])
        self.assertIn("already paired", payload["error"])

    def test_observe_clients_can_read_status_but_cannot_control(self):
        exit_code, stdout = self._run_command(
            self.cli.cmd_pair,
            argparse.Namespace(device="observer-phone", capabilities="observe"),
        )
        self.assertEqual(exit_code, 0)
        self.assertTrue(json.loads(stdout)["success"])

        snapshot = {
            "status": "stopped",
            "mode": "paused",
            "hashrate_hs": 0,
            "temperature": 45.0,
            "uptime_seconds": 0,
            "freshness": "2026-03-21T14:00:27.747124+00:00",
        }

        with mock.patch.object(self.cli, "daemon_call", return_value=snapshot) as daemon_call:
            exit_code, stdout = self._run_command(
                self.cli.cmd_status,
                argparse.Namespace(client="observer-phone"),
            )

        self.assertEqual(exit_code, 0)
        self.assertEqual(json.loads(stdout)["status"], "stopped")
        daemon_call.assert_called_once_with("GET", "/status")

        with mock.patch.object(self.cli, "daemon_call") as daemon_call:
            exit_code, stdout = self._run_command(
                self.cli.cmd_control,
                argparse.Namespace(
                    client="observer-phone",
                    action="set_mode",
                    mode="balanced",
                ),
            )

        self.assertEqual(exit_code, 1)
        payload = json.loads(stdout)
        self.assertFalse(payload["success"])
        self.assertEqual(payload["error"], "unauthorized")
        daemon_call.assert_not_called()

        event_kinds = [event.kind for event in self.spine.get_events()]
        self.assertNotIn(self.spine.EventKind.CONTROL_RECEIPT.value, event_kinds)

    def test_control_command_appends_control_receipt_on_success(self):
        exit_code, stdout = self._run_command(
            self.cli.cmd_pair,
            argparse.Namespace(device="controller-phone", capabilities="observe,control"),
        )
        self.assertEqual(exit_code, 0)
        self.assertTrue(json.loads(stdout)["success"])

        daemon_result = {"success": True, "mode": "balanced"}
        with mock.patch.object(self.cli, "daemon_call", return_value=daemon_result) as daemon_call:
            exit_code, stdout = self._run_command(
                self.cli.cmd_control,
                argparse.Namespace(
                    client="controller-phone",
                    action="set_mode",
                    mode="balanced",
                ),
            )

        self.assertEqual(exit_code, 0)
        payload = json.loads(stdout)
        self.assertTrue(payload["acknowledged"])
        daemon_call.assert_called_once_with("POST", "/miner/set_mode", {"mode": "balanced"})

        latest_event = self.spine.get_events(limit=1)[0]
        self.assertEqual(latest_event.kind, self.spine.EventKind.CONTROL_RECEIPT.value)
        self.assertEqual(latest_event.payload["command"], "set_mode")
        self.assertEqual(latest_event.payload["mode"], "balanced")
        self.assertEqual(latest_event.payload["status"], "accepted")
        self.assertIn("receipt_id", latest_event.payload)


if __name__ == "__main__":
    unittest.main()
