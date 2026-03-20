#!/bin/bash
#
# read_miner_status.sh - Read live miner status from Zend Home
#
# Usage:
#   ./scripts/read_miner_status.sh --client <name>
#
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(dirname "$SCRIPT_DIR")"
DAEMON_DIR="$ROOT_DIR/services/home-miner-daemon"
STATE_DIR="$ROOT_DIR/state"
DAEMON_URL="${ZEND_DAEMON_URL:-http://127.0.0.1:${ZEND_BIND_PORT:-8080}}"

# Parse arguments
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

# Read status via CLI
export ZEND_STATE_DIR="$STATE_DIR"
export ZEND_DAEMON_URL="$DAEMON_URL"
cd "$DAEMON_DIR"
set +e
OUTPUT=$(python3 cli.py status --client "$CLIENT" 2>&1)
RESULT=$?
set -e

if [ $RESULT -ne 0 ]; then
    echo "$OUTPUT"
    exit 1
fi

# Parse and format output
echo "$OUTPUT"

# Extract key fields for script-friendly output
STATUS=$(echo "$OUTPUT" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('status', 'unknown'))" 2>/dev/null || echo "unknown")
MODE=$(echo "$OUTPUT" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('mode', 'unknown'))" 2>/dev/null || echo "unknown")
FRESHNESS=$(echo "$OUTPUT" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('freshness', ''))" 2>/dev/null || echo "")

echo ""
echo "status=$STATUS"
echo "mode=$MODE"
if [ -n "$FRESHNESS" ]; then
    echo "freshness=$FRESHNESS"
fi
