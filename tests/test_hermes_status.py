import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[1]
STATUS_SCRIPT = ROOT_DIR / "scripts" / "hermes_status.sh"


class HermesStatusScriptTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.state_dir = Path(self.temp_dir.name)
        (self.state_dir / "hermes").mkdir(parents=True, exist_ok=True)

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
        (self.state_dir / "hermes" / "principal.json").write_text(
            json.dumps(principal),
            encoding="utf-8",
        )
        return principal

    def write_spine(self, *events):
        if not events:
            return
        payload = "\n".join(json.dumps(event) for event in events) + "\n"
        (self.state_dir / "event-spine.jsonl").write_text(payload, encoding="utf-8")

    def write_pid(self, pid):
        (self.state_dir / "daemon.pid").write_text(f"{pid}\n", encoding="utf-8")

    def run_status(self):
        env = os.environ.copy()
        env["ZEND_STATE_DIR"] = str(self.state_dir)
        env["ZEND_BIND_HOST"] = "127.0.0.1"
        env["ZEND_BIND_PORT"] = "65534"
        return subprocess.run(
            ["bash", str(STATUS_SCRIPT)],
            cwd=ROOT_DIR,
            env=env,
            capture_output=True,
            text=True,
            check=False,
        )

    def test_reports_foreign_pid_as_stale(self):
        self.write_principal()
        self.write_spine(
            {
                "id": "evt-1",
                "principal_id": "hermes-adapter-001",
                "kind": "hermes_summary",
                "payload": {"summary_text": "status smoke", "authority_scope": ["observe"]},
                "created_at": "2026-03-20T01:00:00Z",
                "version": 1,
            }
        )
        self.write_pid(os.getpid())

        result = self.run_status()

        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        self.assertIn("daemon_pid_status=stale", result.stdout)
        self.assertIn("daemon_endpoint=skipped", result.stdout)
        self.assertIn("issues=daemon_not_running", result.stdout)

    def test_counts_only_matching_hermes_summary_events(self):
        principal = self.write_principal()
        self.write_spine(
            {
                "id": "evt-other",
                "principal_id": "someone-else",
                "kind": "hermes_summary",
                "payload": {"summary_text": "other summary", "authority_scope": ["observe"]},
                "created_at": "2026-03-20T01:00:00Z",
                "version": 1,
            },
            {
                "id": "evt-match",
                "principal_id": principal["principal_id"],
                "kind": "hermes_summary",
                "payload": {"summary_text": "matching summary", "authority_scope": ["observe"]},
                "created_at": "2026-03-20T02:00:00Z",
                "version": 1,
            },
        )

        result = self.run_status()

        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        self.assertIn("hermes_summary_count=1", result.stdout)
        self.assertIn("last_hermes_summary_at=2026-03-20T02:00:00Z", result.stdout)


if __name__ == "__main__":
    unittest.main()
