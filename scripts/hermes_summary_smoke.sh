#!/bin/bash
#
# hermes_summary_smoke.sh - Test Hermes adapter summary append
#
# Usage:
#   ./scripts/hermes_summary_smoke.sh --client <name> [--hermes-id <id>]
#
# This script:
#   1. Pairs a Hermes agent if not already paired
#   2. Appends a summary through the Hermes adapter
#   3. Verifies the summary appears in the filtered event list
#   4. Verifies user_message events are blocked from Hermes reads
#
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(dirname "$SCRIPT_DIR")"
DAEMON_DIR="$ROOT_DIR/services/home-miner-daemon"
STATE_DIR="$ROOT_DIR/state"

# Parse arguments
CLIENT=""
HERMES_ID="hermes-smoke-test"
while [[ $# -gt 0 ]]; do
    case $1 in
        --client)
            CLIENT="$2"
            shift 2
            ;;
        --hermes-id)
            HERMES_ID="$2"
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
    echo "Usage: $0 --client <name> [--hermes-id <id>]"
    exit 1
fi

export ZEND_STATE_DIR="$STATE_DIR"
cd "$DAEMON_DIR"

SUMMARY_TEXT="Test Hermes summary: miner has been running for 1 hour in balanced mode"

# Run the full smoke test in one Python process to avoid shell quoting hell
python3 << 'PYEOF'
import sys, json, os
sys.path.insert(0, '.')
os.environ['ZEND_STATE_DIR'] = os.environ.get('ZEND_STATE_DIR', 'state')

import hermes
import spine
from store import load_or_create_principal

CLIENT = sys.argv[1] if len(sys.argv) > 1 else 'alice-phone'
HERMES_ID = sys.argv[2] if len(sys.argv) > 2 else 'hermes-smoke-test'
SUMMARY_TEXT = "Test Hermes summary: miner has been running for 1 hour in balanced mode"

print(f"[1] Pairing Hermes agent: {HERMES_ID}")
conn = hermes.pair_hermes(HERMES_ID, CLIENT)
token = hermes.build_authority_token(conn, expires_in_hours=1)
print(f"    Paired. principal_id={conn.principal_id}")

print(f"[2] Connecting with authority token...")
conn2 = hermes.connect(token)
print(f"    Connected as hermes_id={conn2.hermes_id}, caps={conn2.capabilities}")

print(f"[3] Appending Hermes summary...")
result = hermes.append_summary(conn2, SUMMARY_TEXT)
event_id = result['event_id']
print(f"    Appended. event_id={event_id}")

print(f"[4] Verifying summary in filtered event list...")
events = hermes.get_filtered_events(conn2, limit=20)
event_ids = [e['id'] for e in events]
kinds = [e['kind'] for e in events]
if event_id in event_ids:
    print(f"    ✓ Summary found in filtered events")
else:
    print(f"    ✗ Summary NOT in filtered events")
    sys.exit(1)

if 'user_message' in kinds:
    print(f"    ✗ user_message leaked into Hermes-filtered events!")
    sys.exit(1)
else:
    print(f"    ✓ user_message correctly blocked")

# Also seed a user_message and verify it's filtered
principal = load_or_create_principal()
spine.append_event(
    spine.EventKind.USER_MESSAGE,
    principal.id,
    {"thread_id": "t1", "sender_id": "alice", "encrypted_content": "secret"}
)
events_after = hermes.get_filtered_events(conn2, limit=50)
kinds_after = [e['kind'] for e in events_after]
if 'user_message' in kinds_after:
    print(f"    ✗ user_message still present after seeding!")
    sys.exit(1)
else:
    print(f"    ✓ user_message filtered even after seeding")

print()
print("summary_appended_to_operations_inbox=true")
print("hermes_event_filter_verified=true")
PYEOF

echo ""
echo "---"
echo "Hermes adapter smoke test: PASSED"
