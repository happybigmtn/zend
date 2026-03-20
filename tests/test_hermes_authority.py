import json
import sys
import tempfile
import unittest
from pathlib import Path


SERVICE_DIR = Path(__file__).resolve().parents[1] / "services" / "home-miner-daemon"
sys.path.insert(0, str(SERVICE_DIR))

import spine  # noqa: E402


class HermesAuthorityTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)

        self.state_dir = Path(self.temp_dir.name)
        self.original_state_dir = spine.STATE_DIR
        self.original_spine_file = spine.SPINE_FILE
        self.original_hermes_principal_file = spine.HERMES_PRINCIPAL_FILE

        spine.STATE_DIR = str(self.state_dir)
        spine.SPINE_FILE = str(self.state_dir / "event-spine.jsonl")
        spine.HERMES_PRINCIPAL_FILE = str(self.state_dir / "hermes" / "principal.json")

        self.addCleanup(self.restore_spine_state)

    def restore_spine_state(self):
        spine.STATE_DIR = self.original_state_dir
        spine.SPINE_FILE = self.original_spine_file
        spine.HERMES_PRINCIPAL_FILE = self.original_hermes_principal_file

    def write_principal(self, **overrides):
        principal = {
            "principal_id": "hermes-adapter-001",
            "name": "Hermes Gateway Adapter",
            "capabilities": ["observe"],
            "authority_scope": ["observe"],
            "summary_append_enabled": True,
            "created_at": "2026-03-20T00:00:00Z",
            "milestone": 1,
            "note": "Hermes milestone 1",
        }
        principal.update(overrides)

        principal_path = Path(spine.HERMES_PRINCIPAL_FILE)
        principal_path.parent.mkdir(parents=True, exist_ok=True)
        principal_path.write_text(json.dumps(principal), encoding="utf-8")
        return principal

    def read_spine_events(self):
        spine_path = Path(spine.SPINE_FILE)
        if not spine_path.exists():
            return []
        return [
            json.loads(line)
            for line in spine_path.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]

    def test_append_hermes_summary_authorized_writes_observe_only_event(self):
        principal = self.write_principal()

        event = spine.append_hermes_summary_authorized(
            "Hermes delegated summary",
            principal["principal_id"],
        )

        self.assertEqual(event.kind, spine.EventKind.HERMES_SUMMARY.value)
        self.assertEqual(event.principal_id, principal["principal_id"])
        self.assertEqual(event.payload["authority_scope"], ["observe"])

        events = self.read_spine_events()
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0]["payload"]["authority_scope"], ["observe"])

    def test_append_hermes_summary_authorized_rejects_scope_escalation(self):
        principal = self.write_principal()

        with self.assertRaisesRegex(spine.GatewayUnauthorized, "not delegated"):
            spine.append_hermes_summary_authorized(
                "Hermes delegated summary",
                principal["principal_id"],
                ["observe", "control"],
            )

        self.assertEqual(self.read_spine_events(), [])

    def test_append_hermes_summary_authorized_rejects_disabled_summary_append(self):
        principal = self.write_principal(summary_append_enabled=False)

        with self.assertRaisesRegex(spine.GatewayUnauthorized, "disabled"):
            spine.append_hermes_summary_authorized(
                "Hermes delegated summary",
                principal["principal_id"],
            )

        self.assertEqual(self.read_spine_events(), [])

    def test_append_hermes_summary_authorized_rejects_milestone_boundary_drift(self):
        principal = self.write_principal(
            capabilities=["observe", "control"],
            authority_scope=["observe", "control"],
        )

        with self.assertRaisesRegex(spine.GatewayUnauthorized, "milestone 1 authority"):
            spine.append_hermes_summary_authorized(
                "Hermes delegated summary",
                principal["principal_id"],
            )

        self.assertEqual(self.read_spine_events(), [])


if __name__ == "__main__":
    unittest.main()
