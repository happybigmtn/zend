#!/bin/bash
#
# read_events.sh - Read events from the Zend Home event spine
#
# Usage:
#   ./scripts/read_events.sh [--client <name>] [--kind <kind>] [--limit <n>]
#
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(dirname "$SCRIPT_DIR")"
DAEMON_DIR="$ROOT_DIR/services/home-miner-daemon"
STATE_DIR="$ROOT_DIR/state"
DAEMON_URL="${ZEND_DAEMON_URL:-http://127.0.0.1:${ZEND_BIND_PORT:-8080}}"

CLIENT=""
KIND=""
LIMIT="100"

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --client)
            CLIENT="$2"
            shift 2
            ;;
        --kind)
            KIND="$2"
            shift 2
            ;;
        --limit)
            LIMIT="$2"
            shift 2
            ;;
        *)
            echo "Unknown option: $1"
            exit 1
            ;;
    esac
done

# Build query string
QUERY_PARAMS=""
if [ -n "$CLIENT" ]; then
    QUERY_PARAMS="${QUERY_PARAMS}client=${CLIENT}&"
fi
if [ -n "$KIND" ]; then
    QUERY_PARAMS="${QUERY_PARAMS}kind=${KIND}&"
fi
QUERY_PARAMS="${QUERY_PARAMS}limit=${LIMIT}"

# Fetch events from daemon
URL="${DAEMON_URL}/events"
if [ -n "$QUERY_PARAMS" ]; then
    URL="${URL}?${QUERY_PARAMS}"
fi

set +e
RESPONSE=$(curl -s -w "\n%{http_code}" "$URL" 2>&1)
HTTP_CODE=$(echo "$RESPONSE" | tail -n1)
BODY=$(echo "$RESPONSE" | sed '$d')

if [ "$HTTP_CODE" -eq 200 ]; then
    echo "$BODY" | python3 -c "
import sys, json
data = json.load(sys.stdin)
events = data.get('events', [])
count = data.get('count', 0)
print(f'Events: {count}')
print()
for e in events:
    kind = e.get('kind', 'unknown')
    created = e.get('created_at', '')
    payload = e.get('payload', {})
    print(f'[{created}] {kind}')
    for k, v in payload.items():
        print(f'  {k}: {v}')
    print()
"
    RESULT=0
else
    echo "$BODY" | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    print(data.get('error', 'unknown error'))
    print(data.get('message', ''))
except:
    print('Failed to fetch events')
"
    RESULT=1
fi
set -e

exit $RESULT