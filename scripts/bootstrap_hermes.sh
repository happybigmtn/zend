#!/bin/bash
#
# bootstrap_hermes.sh - Bootstrap the Hermes adapter slice
#
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(dirname "$SCRIPT_DIR")"
ADAPTER_DIR="$ROOT_DIR/services/hermes-adapter"
STATE_DIR="$ROOT_DIR/state"
ADAPTER_STATE="$STATE_DIR/hermes-adapter-state.json"

mkdir -p "$STATE_DIR"
mkdir -p "$ADAPTER_DIR"

if [ ! -f "$ADAPTER_STATE" ]; then
    cat > "$ADAPTER_STATE" <<'EOF'
{
  "version": 1,
  "adapter_id": "hermes-adapter-001",
  "authority_scope": ["observe", "summarize"],
  "connected": false,
  "connected_at": null,
  "last_summary_ts": null
}
EOF
    echo "Hermes adapter state initialized at $ADAPTER_STATE"
else
    echo "Hermes adapter state already exists at $ADAPTER_STATE"
fi

cd "$ADAPTER_DIR"

python3 - <<'PY'
import base64
import json
import sys
import tempfile
import time
from pathlib import Path

sys.path.insert(0, ".")

from adapter import HermesAdapter, HermesSummary


def make_token(principal_id, capabilities, expiration):
    payload = {
        "principal_id": principal_id,
        "capabilities": capabilities,
        "expiration": expiration,
    }
    return base64.b64encode(json.dumps(payload).encode("utf-8")).decode("utf-8")


with tempfile.TemporaryDirectory() as tmpdir:
    tmp_path = Path(tmpdir)

    fresh_adapter = HermesAdapter(str(tmp_path / "fresh-state.json"))
    assert [cap.value for cap in fresh_adapter.get_scope()] == ["observe", "summarize"]
    try:
        fresh_adapter.read_status()
    except PermissionError as exc:
        assert "connected" in str(exc)
    else:
        raise AssertionError("Disconnected adapter should reject read_status")

    try:
        fresh_adapter.connect("not-a-valid-token")
    except ValueError as exc:
        assert "format" in str(exc).lower()
    else:
        raise AssertionError("Malformed authority token should be rejected")

    observe_adapter = HermesAdapter(str(tmp_path / "observe-state.json"))
    observe_connection = observe_adapter.connect(
        make_token("hermes-observe", ["observe"], time.time() + 60)
    )
    assert [cap.value for cap in observe_connection.authority_scope] == ["observe"]
    snapshot = observe_adapter.read_status()
    assert snapshot.status == "running"

    try:
        observe_adapter.append_summary(
            HermesSummary(
                id="observe-summary",
                text="observe-only cannot append",
                capabilities=["observe"],
                principal_id="hermes-observe",
                timestamp="2026-03-20T00:00:00Z",
            )
        )
    except PermissionError as exc:
        assert "summarize" in str(exc)
    else:
        raise AssertionError("Observe-only token should reject append_summary")

    summarize_state = tmp_path / "summarize-state.json"
    summarize_adapter = HermesAdapter(str(summarize_state))
    summarize_connection = summarize_adapter.connect(
        make_token("hermes-summarize", ["summarize"], time.time() + 60)
    )
    assert [cap.value for cap in summarize_connection.authority_scope] == ["summarize"]

    summary_timestamp = "2026-03-20T00:00:00Z"
    summarize_adapter.append_summary(
        HermesSummary(
            id="summary-ok",
            text="Hermes summary",
            capabilities=["summarize"],
            principal_id="hermes-summarize",
            timestamp=summary_timestamp,
        )
    )
    persisted_state = json.loads(summarize_state.read_text())
    assert persisted_state["last_summary_ts"] == summary_timestamp

    try:
        summarize_adapter.read_status()
    except PermissionError as exc:
        assert "observe" in str(exc)
    else:
        raise AssertionError("Summarize-only token should reject read_status")

    expired_adapter = HermesAdapter(str(tmp_path / "expired-state.json"))
    try:
        expired_adapter.connect(
            make_token("hermes-expired", ["observe"], time.time() - 60)
        )
    except ValueError as exc:
        assert "expired" in str(exc).lower()
    else:
        raise AssertionError("Expired authority token should be rejected")

print("Hermes adapter proof: OK")
PY

echo ""
echo "Hermes adapter bootstrap complete"
echo "adapter_state_file=$ADAPTER_STATE"
echo "bootstrap=success"
