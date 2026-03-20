#!/bin/bash
#
# pair_gateway_client.sh - Pair a gateway client with Zend Home
#
# Usage:
#   ./scripts/pair_gateway_client.sh --client <name> [--capabilities observe,control]
#
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(dirname "$SCRIPT_DIR")"
DAEMON_DIR="$ROOT_DIR/services/home-miner-daemon"
STATE_DIR="$ROOT_DIR/state"
DAEMON_URL="${ZEND_DAEMON_URL:-http://127.0.0.1:${ZEND_BIND_PORT:-8080}}"

# Default capabilities
CAPABILITIES="observe"

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --client)
            CLIENT="$2"
            shift 2
            ;;
        --capabilities)
            CAPABILITIES="$2"
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
    echo "Usage: $0 --client <name> [--capabilities observe,control]"
    exit 1
fi

# Run pairing via CLI (idempotent: skips if device already paired)
export ZEND_STATE_DIR="$STATE_DIR"
export ZEND_DAEMON_URL="$DAEMON_URL"
cd "$DAEMON_DIR"
set +e

# Check if already paired (idempotency)
EXISTING=$(python3 -c "
import sys, json
sys.path.insert(0, '.')
from store import get_pairing_by_device
p = get_pairing_by_device('$CLIENT')
if p:
    print(json.dumps({'device_name': p.device_name, 'capabilities': p.capabilities, 'paired_at': p.paired_at}))
else:
    print('{}')
" 2>&1)

if [ -n "$EXISTING" ] && [ "$EXISTING" != "{}" ]; then
    DEVICE_NAME=$(echo "$EXISTING" | python3 -c "import sys,json; print(json.load(sys.stdin).get('device_name', '$CLIENT'))" 2>/dev/null || echo "$CLIENT")
    CAPS=$(echo "$EXISTING" | python3 -c "import sys,json; print(','.join(json.load(sys.stdin).get('capabilities', ['observe'])))" 2>/dev/null || echo "observe")
    echo "{\"success\": true, \"device_name\": \"$DEVICE_NAME\", \"capabilities\": [\"$CAPS\"]}"
    echo ""
    echo "paired $DEVICE_NAME"
    echo "capability=$CAPS"
    exit 0
fi

OUTPUT=$(python3 cli.py pair --device "$CLIENT" --capabilities "$CAPABILITIES" 2>&1)
RESULT=$?
set -e

echo "$OUTPUT"

if [ $RESULT -eq 0 ]; then
    # Parse output for success message
    DEVICE_NAME=$(echo "$OUTPUT" | python3 -c "import sys,json; print(json.load(sys.stdin).get('device_name', '$CLIENT'))" 2>/dev/null || echo "$CLIENT")
    echo ""
    echo "paired $DEVICE_NAME"
    echo "capability=$(echo "$OUTPUT" | python3 -c "import sys,json; print(','.join(json.load(sys.stdin).get('capabilities', ['observe'])))" 2>/dev/null || echo "observe")"
    exit 0
else
    exit $RESULT
fi
