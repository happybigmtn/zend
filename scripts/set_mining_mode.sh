#!/bin/bash
#
# set_mining_mode.sh - Set mining mode on Zend Home
#
# Usage:
#   ./scripts/set_mining_mode.sh --client <name> --mode <paused|balanced|performance>
#   ./scripts/set_mining_mode.sh --client <name> --action <start|stop>
#
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(dirname "$SCRIPT_DIR")"
DAEMON_DIR="$ROOT_DIR/services/home-miner-daemon"
STATE_DIR="$ROOT_DIR/state"
DAEMON_URL="${ZEND_DAEMON_URL:-http://127.0.0.1:${ZEND_BIND_PORT:-8080}}"

CLIENT=""
ACTION=""
MODE=""

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --client)
            CLIENT="$2"
            shift 2
            ;;
        --mode)
            MODE="$2"
            ACTION="set_mode"
            shift 2
            ;;
        --action)
            ACTION="$2"
            shift 2
            ;;
        --start)
            ACTION="start"
            shift
            ;;
        --stop)
            ACTION="stop"
            shift
            ;;
        *)
            echo "Unknown option: $1"
            exit 1
            ;;
    esac
done

if [ -z "$CLIENT" ]; then
    echo "Error: --client is required"
    echo "Usage: $0 --client <name> --mode <paused|balanced|performance>"
    echo "       $0 --client <name> --action <start|stop>"
    exit 1
fi

if [ -z "$ACTION" ]; then
    echo "Error: Either --mode or --action is required"
    exit 1
fi

# Validate mode
if [ "$ACTION" = "set_mode" ]; then
    case "$MODE" in
        paused|balanced|performance)
            ;;
        *)
            echo "Error: Invalid mode. Must be paused, balanced, or performance"
            exit 1
            ;;
    esac
fi

# Run control via CLI
export ZEND_STATE_DIR="$STATE_DIR"
export ZEND_DAEMON_URL="$DAEMON_URL"
cd "$DAEMON_DIR"

set +e
if [ "$ACTION" = "set_mode" ]; then
    OUTPUT=$(python3 cli.py control --client "$CLIENT" --action set_mode --mode "$MODE" 2>&1)
else
    OUTPUT=$(python3 cli.py control --client "$CLIENT" --action "$ACTION" 2>&1)
fi
RESULT=$?
set -e

echo "$OUTPUT"

if [ $RESULT -eq 0 ]; then
    # Show success message
    ACKNOWLEDGED=$(echo "$OUTPUT" | python3 -c "import sys,json; print(json.load(sys.stdin).get('acknowledged', False))" 2>/dev/null || echo "false")
    if [ "$ACKNOWLEDGED" = "True" ]; then
        echo ""
        echo "acknowledged=true"
        echo "note='Action accepted by home miner, not client device'"
    fi
    exit 0
else
    # Check for authorization error
    ERROR=$(echo "$OUTPUT" | python3 -c "import sys,json; print(json.load(sys.stdin).get('error', ''))" 2>/dev/null || echo "")
    if [ "$ERROR" = "unauthorized" ]; then
        echo ""
        echo "Error: Client lacks 'control' capability"
    fi
    exit 1
fi
