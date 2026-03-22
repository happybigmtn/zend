#!/bin/bash
#
# hermes_summary_smoke.sh - Test Hermes adapter summary append
#
# Usage:
#   ./scripts/hermes_summary_smoke.sh [--client <name>]
#
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(dirname "$SCRIPT_DIR")"
DAEMON_DIR="$ROOT_DIR/services/home-miner-daemon"
STATE_DIR="$ROOT_DIR/state"

# Parse arguments
CLIENT="${CLIENT:-hermes-test}"
HERMES_ID="${HERMES_ID:-hermes-smoke-test}"

# Setup state directory
export ZEND_STATE_DIR="$STATE_DIR"
mkdir -p "$STATE_DIR"

cd "$DAEMON_DIR"

echo "=== Hermes Adapter Smoke Test ==="
echo ""

# Step 1: Pair Hermes
echo "1. Pairing Hermes agent..."
PAIR_RESULT=$(python3 cli.py hermes pair --hermes-id "$HERMES_ID" --device-name "smoke-test-agent" 2>&1)
echo "$PAIR_RESULT"
if ! echo "$PAIR_RESULT" | grep -q '"success": true'; then
    echo "ERROR: Hermes pairing failed"
    exit 1
fi
echo ""

# Step 2: Generate authority token
echo "2. Generating authority token..."
TOKEN_RESULT=$(python3 cli.py hermes token --hermes-id "$HERMES_ID" 2>&1)
echo "$TOKEN_RESULT"
TOKEN=$(echo "$TOKEN_RESULT" | python3 -c "import json,sys; print(json.load(sys.stdin)['authority_token'])")
echo ""

# Step 3: Connect Hermes to daemon
echo "3. Connecting Hermes to daemon..."
CONNECT_RESULT=$(curl -s -X POST http://127.0.0.1:8080/hermes/connect \
    -H "Content-Type: application/json" \
    -d "{\"authority_token\": $TOKEN}" 2>&1)
echo "$CONNECT_RESULT"
if ! echo "$CONNECT_RESULT" | grep -q '"connected": true'; then
    echo "ERROR: Hermes connection failed"
    exit 1
fi
echo ""

# Step 4: Read status via Hermes adapter
echo "4. Reading miner status via Hermes adapter..."
STATUS_RESULT=$(curl -s -H "Authorization: Hermes $HERMES_ID" http://127.0.0.1:8080/hermes/status 2>&1)
echo "$STATUS_RESULT"
echo ""

# Step 5: Append summary
echo "5. Appending Hermes summary..."
SUMMARY_TEXT="Test Hermes summary: miner has been running for 1 hour in balanced mode"
SUMMARY_RESULT=$(curl -s -X POST http://127.0.0.1:8080/hermes/summary \
    -H "Authorization: Hermes $HERMES_ID" \
    -H "Content-Type: application/json" \
    -d "{\"summary_text\": \"$SUMMARY_TEXT\", \"authority_scope\": \"observe\"}" 2>&1)
echo "$SUMMARY_RESULT"
if ! echo "$SUMMARY_RESULT" | grep -q '"appended": true'; then
    echo "ERROR: Summary append failed"
    exit 1
fi
echo ""

# Step 6: Read filtered events
echo "6. Reading filtered events (should see hermes_summary, NOT user_message)..."
EVENTS_RESULT=$(curl -s -H "Authorization: Hermes $HERMES_ID" http://127.0.0.1:8080/hermes/events 2>&1)
echo "$EVENTS_RESULT"
if echo "$EVENTS_RESULT" | grep -q '"user_message"'; then
    echo "ERROR: Hermes can see user_message events (should be filtered)"
    exit 1
fi
echo ""

# Step 7: Verify control is blocked
echo "7. Verifying Hermes CANNOT issue control commands..."
CONTROL_RESULT=$(curl -s -X POST http://127.0.0.1:8080/miner/start \
    -H "Authorization: Hermes $HERMES_ID" 2>&1)
echo "$CONTROL_RESULT"
if ! echo "$CONTROL_RESULT" | grep -q '"HERMES_UNAUTHORIZED"'; then
    echo "ERROR: Hermes should NOT be able to issue control commands"
    exit 1
fi
echo ""

echo "=== All Hermes adapter smoke tests PASSED ==="
echo ""
echo "summary_appended_to_operations_inbox=true"
