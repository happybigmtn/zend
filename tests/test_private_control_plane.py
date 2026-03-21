#!/usr/bin/env python3

import contextlib
import importlib
import io
import os
import sys
import tempfile
import unittest
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[1]
DAEMON_DIR = ROOT_DIR / "services" / "home-miner-daemon"

if str(DAEMON_DIR) not in sys.path:
    sys.path.insert(0, str(DAEMON_DIR))


def load_modules(state_dir: str):
    os.environ["ZEND_STATE_DIR"] = state_dir

    store = importlib.import_module("store")
    spine = importlib.import_module("spine")
    daemon = importlib.import_module("daemon")
    cli = importlib.import_module("cli")

    store = importlib.reload(store)
    spine = importlib.reload(spine)
    daemon = importlib.reload(daemon)
    cli = importlib.reload(cli)
    return store, spine, daemon, cli


class PrivateControlPlaneTest(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.previous_state_dir = os.environ.get("ZEND_STATE_DIR")
        self.addCleanup(self._restore_env)
        self.store, self.spine, self.daemon, self.cli = load_modules(self.temp_dir.name)

    def _restore_env(self):
        if self.previous_state_dir is None:
            os.environ.pop("ZEND_STATE_DIR", None)
            return
        os.environ["ZEND_STATE_DIR"] = self.previous_state_dir

    def test_inbox_projection_filters_non_inbox_events(self):
        principal = self.store.load_or_create_principal()

        self.spine.append_pairing_granted("alice-phone", ["observe"], principal.id)
        self.spine.append_control_receipt("set_mode", "balanced", "accepted", principal.id)
        self.spine.append_hermes_summary("Balanced summary", ["observe"], principal.id)
        self.spine.append_miner_alert("health_warning", "Temp elevated", principal.id)

        inbox_kinds = [event.kind for event in self.spine.get_events(surface="inbox")]
        self.assertEqual(
            inbox_kinds,
            ["miner_alert", "hermes_summary", "control_receipt"],
        )

        device_pairing_kinds = [
            event.kind for event in self.spine.get_events(surface="device_pairing")
        ]
        self.assertEqual(device_pairing_kinds, ["pairing_granted"])

    def test_spine_events_route_helper_returns_projection_and_checks_observe_scope(self):
        principal = self.store.load_or_create_principal()
        self.store.pair_client("observer-phone", ["observe"])

        self.spine.append_pairing_granted("observer-phone", ["observe"], principal.id)
        self.spine.append_control_receipt("set_mode", "balanced", "accepted", principal.id)
        self.spine.append_hermes_summary("Balanced summary", ["observe"], principal.id)

        status, payload = self.daemon.read_spine_events(
            client="observer-phone",
            surface="inbox",
            limit_raw="10",
        )

        self.assertEqual(status, 200)
        self.assertEqual(
            [event["kind"] for event in payload["events"]],
            ["hermes_summary", "control_receipt"],
        )
        self.assertIn("principal_id", payload["events"][0])

        status, payload = self.daemon.read_spine_events()

        self.assertEqual(status, 200)
        self.assertEqual(
            [event["kind"] for event in payload["events"]],
            ["hermes_summary", "control_receipt", "pairing_granted"],
        )

        status, error_payload = self.daemon.read_spine_events(client="unknown-device")
        self.assertEqual(status, 403)
        self.assertEqual(error_payload["error"], "unauthorized")

    def test_bootstrap_reuses_existing_device_pairing_without_duplicate_event(self):
        args = type("Args", (), {"device": "bootstrap-phone"})()

        first_stdout = io.StringIO()
        with contextlib.redirect_stdout(first_stdout):
            first_status = self.cli.cmd_bootstrap(args)

        second_stdout = io.StringIO()
        with contextlib.redirect_stdout(second_stdout):
            second_status = self.cli.cmd_bootstrap(args)

        self.assertEqual(first_status, 0)
        self.assertEqual(second_status, 0)

        pairings = self.store.load_pairings()
        self.assertEqual(len(pairings), 1)

        pairing_events = [
            event for event in self.spine.get_events(kind="pairing_granted")
            if event.payload["device_name"] == "bootstrap-phone"
        ]
        self.assertEqual(len(pairing_events), 1)
        self.assertIn('"device_name": "bootstrap-phone"', second_stdout.getvalue())


if __name__ == "__main__":
    unittest.main()
