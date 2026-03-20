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
DAEMON_DIR="$ROOT_DIR/services/home-miner-daemon"
STATE_DIR="$ROOT_DIR/state"
HERMES_TOKEN_PATH="$STATE_DIR/hermes-gateway.authority-token"
DAEMON_URL="${ZEND_DAEMON_URL:-http://127.0.0.1:${ZEND_BIND_PORT:-8080}}"

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

# Ensure Hermes delegated authority exists
if [ ! -f "$HERMES_TOKEN_PATH" ]; then
    "$ROOT_DIR/scripts/bootstrap_hermes.sh" > /dev/null
fi

export ZEND_STATE_DIR="$STATE_DIR"
export ZEND_DAEMON_URL="$DAEMON_URL"
export PYTHONPATH="$ROOT_DIR/services:$DAEMON_DIR${PYTHONPATH:+:$PYTHONPATH}"
export ROOT_DIR
export CLIENT

cd "$ROOT_DIR"

python3 -c "
import os
import sys
from pathlib import Path
sys.path.insert(0, str(Path(os.environ['ROOT_DIR']) / 'services' / 'home-miner-daemon'))
from store import get_pairing_by_device

pairing = get_pairing_by_device(os.environ['CLIENT'])
if pairing is None:
    raise SystemExit(f\"Error: client '{os.environ['CLIENT']}' is not paired\")
" >/dev/null

# Create a summary payload
SUMMARY_TEXT="Hermes smoke summary for $CLIENT via delegated adapter access"
TOKEN="$(tr -d '\n' < "$HERMES_TOKEN_PATH")"

SCOPE_OUTPUT="$(python3 -m hermes_adapter.adapter scope --token "$TOKEN")"

set +e
SUMMARY_OUTPUT="$(python3 -m hermes_adapter.adapter summarize --token "$TOKEN" --text "$SUMMARY_TEXT" 2>&1)"
RESULT=$?
set -e

echo "$SCOPE_OUTPUT"
echo "$SUMMARY_OUTPUT"

if [ $RESULT -ne 0 ]; then
    exit $RESULT
fi

export SUMMARY_TEXT
EVENT_OUTPUT="$(python3 -c "
import json
import os
from pathlib import Path

spine_path = Path(os.environ['ZEND_STATE_DIR']) / 'event-spine.jsonl'
summary_text = os.environ['SUMMARY_TEXT']

if not spine_path.exists():
    raise SystemExit('Error: event spine does not exist')

for raw_line in reversed(spine_path.read_text().splitlines()):
    if not raw_line.strip():
        continue
    event = json.loads(raw_line)
    payload = event.get('payload', {})
    if event.get('kind') == 'hermes_summary' and payload.get('summary_text') == summary_text:
        print(json.dumps({
            'event_id': event['id'],
            'principal_id': event['principal_id'],
            'summary_text': payload.get('summary_text'),
            'authority_scope': payload.get('authority_scope', []),
        }, indent=2))
        break
else:
    raise SystemExit('Error: delegated Hermes summary was not written to the event spine')
")"

echo ""
echo "$EVENT_OUTPUT"
echo ""
echo "summary_appended_to_operations_inbox=true"
echo "source=hermes_adapter"
