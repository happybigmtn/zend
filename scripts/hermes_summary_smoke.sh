#!/bin/bash
#
# hermes_summary_smoke.sh - Test Hermes adapter summary append
#
# Usage:
#   ./scripts/hermes_summary_smoke.sh --client <name>
#
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(dirname "$SCRIPT_DIR")"
STATE_DIR="${ZEND_STATE_DIR:-$ROOT_DIR/state}"
ADAPTER_STATE="$STATE_DIR/hermes-adapter-state.json"

# Parse arguments
CLIENT=""
while [[ $# -gt 0 ]]; do
    case $1 in
        --client)
            CLIENT="$2"
            shift 2
            ;;
        *)
            echo "Unknown option: $1"
            exit 1
            ;;
    esac
done

if [ -z "$CLIENT" ]; then
    echo "Error: --client is required"
    echo "Usage: $0 --client <name>"
    exit 1
fi

mkdir -p "$STATE_DIR"

# Add a Hermes summary through the Hermes adapter
export ZEND_STATE_DIR="$STATE_DIR"
export HERMES_ROOT_DIR="$ROOT_DIR"
export HERMES_ADAPTER_STATE="$ADAPTER_STATE"
export HERMES_CLIENT="$CLIENT"

python3 - <<'PY'
import base64
import json
import os
import sys
import time
import uuid
from pathlib import Path

root_dir = Path(os.environ["HERMES_ROOT_DIR"])
sys.path.insert(0, str(root_dir / "services" / "hermes-adapter"))
sys.path.insert(0, str(root_dir / "services" / "home-miner-daemon"))

from adapter import HermesAdapter, HermesSummary
from spine import EventKind, get_events
from store import load_or_create_principal


def make_token(principal_id, capabilities, expiration):
    payload = {
        "principal_id": principal_id,
        "capabilities": capabilities,
        "expiration": expiration,
    }
    return base64.b64encode(json.dumps(payload).encode("utf-8")).decode("utf-8")


principal = load_or_create_principal()
adapter = HermesAdapter(os.environ["HERMES_ADAPTER_STATE"])
adapter.connect(
    make_token(principal.id, ["observe", "summarize"], time.time() + 60)
)

summary_text = (
    f"Hermes summary for {os.environ['HERMES_CLIENT']}: "
    "miner has been running for 1 hour in balanced mode"
)
before_events = get_events(EventKind.HERMES_SUMMARY, limit=20)
summary = HermesSummary(
    id=str(uuid.uuid4()),
    text=summary_text,
    capabilities=["observe", "summarize"],
    principal_id=principal.id,
    timestamp=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
)
adapter.append_summary(summary)

after_events = get_events(EventKind.HERMES_SUMMARY, limit=20)
assert len(after_events) == len(before_events) + 1
newest_event = after_events[0]
assert newest_event.principal_id == principal.id
assert newest_event.payload["summary_text"] == summary_text
assert newest_event.payload["authority_scope"] == ["observe", "summarize"]

adapter.disconnect()
state = json.loads(Path(os.environ["HERMES_ADAPTER_STATE"]).read_text(encoding="utf-8"))
assert state["connected"] is False
assert state["last_summary_ts"] == newest_event.created_at

print(f"event_id={newest_event.id}")
print(f"principal_id={principal.id}")
print(f"client={os.environ['HERMES_CLIENT']}")
PY

echo ""
echo "summary_appended_to_operations_inbox=true"
