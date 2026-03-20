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
ADAPTER_DIR="$ROOT_DIR/services/hermes-adapter"
STATE_DIR="$ROOT_DIR/state"

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

# Add a Hermes summary via the Hermes adapter
export ZEND_STATE_DIR="$STATE_DIR"
export PYTHONPATH="$DAEMON_DIR:$ADAPTER_DIR:$PYTHONPATH"

# Create a summary payload using the HermesAdapter
python3 -c "
import sys
sys.path.insert(0, '$ADAPTER_DIR')
sys.path.insert(0, '$DAEMON_DIR')

from hermes_adapter import HermesAdapter, make_summary_text
from hermes_adapter.token import create_hermes_token
from spine import EventKind, get_events

# Create a Hermes authority token for testing
principal_id = 'test-principal'
capabilities = ['observe', 'summarize']
token_str, token = create_hermes_token(principal_id, capabilities)

# Connect using the adapter
adapter = HermesAdapter()
conn = adapter.connect(token_str)
print(f'connected=true')
print(f'principal_id={conn.principal_id}')
print(f'capabilities={conn.capabilities}')

# Append a summary using the adapter
summary_text = 'Test Hermes summary: miner has been running for 1 hour in balanced mode'
summary = make_summary_text(summary_text, conn.capabilities)
adapter.appendSummary(summary)
print(f'summary_appended=true')

events = get_events(EventKind.HERMES_SUMMARY)
latest = events[0]
if latest.payload.get('summary_text') != summary_text:
    raise SystemExit('latest Hermes summary did not match smoke payload')
print(f'spine_event_verified=true')
"

echo ""
echo "summary_appended_to_operations_inbox=true"
