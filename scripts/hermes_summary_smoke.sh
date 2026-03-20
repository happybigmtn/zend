#!/bin/bash
#
# hermes_summary_smoke.sh - Test Hermes adapter via HTTP API
#
# This script exercises the full Hermes adapter path:
# 1. Creates a Hermes authority token
# 2. Connects via POST /hermes/connect
# 3. Appends a summary via POST /hermes/summary
#
# Usage:
#   ./scripts/hermes_summary_smoke.sh --client <name>
#
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(dirname "$SCRIPT_DIR")"
DAEMON_DIR="$ROOT_DIR/services/home-miner-daemon"
STATE_DIR="$ROOT_DIR/state"

BIND_HOST="${ZEND_BIND_HOST:-127.0.0.1}"
BIND_PORT="${ZEND_BIND_PORT:-8080}"
BASE_URL="http://$BIND_HOST:$BIND_PORT"

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

export ZEND_STATE_DIR="$STATE_DIR"
cd "$DAEMON_DIR"

# Step 1: Create a Hermes authority token
TOKEN_OUTPUT=$(python3 -c "
import sys
sys.path.insert(0, '.')
from adapter import create_hermes_token

token, encoded = create_hermes_token(
    principal_id='test-hermes-principal',
    capabilities=['observe', 'summarize']
)
print(token)
" 2>&1)

if [ $? -ne 0 ]; then
    echo "Error: Failed to create Hermes token"
    echo "$TOKEN_OUTPUT"
    exit 1
fi

# Step 2: Connect via HTTP and get a connection_id
SUMMARY_TEXT="Test Hermes summary: miner has been running for 1 hour in balanced mode"

RESPONSE=$(curl -s -X POST "$BASE_URL/hermes/connect" \
    -H "Content-Type: application/json" \
    -d "{\"authority_token\": \"$TOKEN_OUTPUT\"}")

if echo "$RESPONSE" | grep -q '"error"'; then
    echo "Error: Failed to connect to Hermes adapter"
    echo "$RESPONSE"
    exit 1
fi

CONNECTION_ID=$(echo "$RESPONSE" | python3 -c "import sys, json; print(json.load(sys.stdin)['connection_id'])")
PRINCIPAL_ID=$(echo "$RESPONSE" | python3 -c "import sys, json; print(json.load(sys.stdin)['principal_id'])")

# Step 3: Append summary via HTTP POST /hermes/summary
SUMMARY_RESPONSE=$(curl -s -X POST "$BASE_URL/hermes/summary" \
    -H "Content-Type: application/json" \
    -d "{\"connection_id\": \"$CONNECTION_ID\", \"summary_text\": \"$SUMMARY_TEXT\"}")

if echo "$SUMMARY_RESPONSE" | grep -q '"error"'; then
    echo "Error: Failed to append Hermes summary"
    echo "$SUMMARY_RESPONSE"
    exit 1
fi

EVENT_ID=$(echo "$SUMMARY_RESPONSE" | python3 -c "import sys, json; print(json.load(sys.stdin)['event_id'])")

echo "event_id=$EVENT_ID"
echo "principal_id=$PRINCIPAL_ID"
echo ""
echo "summary_appended_to_operations_inbox=true"
