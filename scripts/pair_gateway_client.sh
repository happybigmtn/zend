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

# Run pairing via CLI
export ZEND_STATE_DIR="$STATE_DIR"
export ZEND_DAEMON_URL="$DAEMON_URL"
cd "$DAEMON_DIR"
OUTPUT=$(python3 cli.py pair --device "$CLIENT" --capabilities "$CAPABILITIES" 2>&1)
RESULT=$?

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
