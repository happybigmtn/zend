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

# Add a Hermes summary via the event spine
cd "$DAEMON_DIR"

# Create a summary payload
SUMMARY_TEXT="Test Hermes summary: miner has been running for 1 hour in balanced mode"
AUTHORITY_SCOPE="observe"

# Use Python to add the event directly (simulating Hermes adapter)
python3 -c "
import sys
sys.path.insert(0, '.')
from store import load_or_create_principal
from spine import append_hermes_summary

principal = load_or_create_principal()
event = append_hermes_summary('$SUMMARY_TEXT', ['$AUTHORITY_SCOPE'], principal.id)
print(f'event_id={event.id}')
print(f'principal_id={principal.id}')
"

echo ""
echo "summary_appended_to_operations_inbox=true"
