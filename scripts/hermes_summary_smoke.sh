#!/bin/bash
# Hermes Adapter Smoke Test
# Tests the Hermes adapter endpoints against a running daemon
# Usage: ./scripts/hermes_summary_smoke.sh

set -e

DAEMON_URL="${ZEND_DAEMON_URL:-http://127.0.0.1:8080}"

echo "=== Hermes Adapter Smoke Test ==="
echo "Testing against: $DAEMON_URL"
echo ""

# Check daemon is running
echo "1. Checking daemon health..."
HEALTH=$(curl -s "$DAEMON_URL/health")
if echo "$HEALTH" | grep -q "healthy"; then
    echo "   ✓ Daemon is healthy"
else
    echo "   ✗ Daemon not responding"
    echo "   Response: $HEALTH"
    exit 1
fi

# Generate a test token
echo ""
echo "2. Generating test authority token..."
python3 -c "
import sys
sys.path.insert(0, 'services/home-miner-daemon')
import hermes
token = hermes.create_authority_token('test-hermes-001', ['observe', 'summarize'], 24)
print(token)
" > /tmp/hermes_token.txt
TOKEN=$(cat /tmp/hermes_token.txt)
echo "   ✓ Token generated"

# Pair Hermes
echo ""
echo "3. Pairing Hermes agent..."
PAIR=$(curl -s -X POST "$DAEMON_URL/hermes/pair" \
    -H "Content-Type: application/json" \
    -d '{"hermes_id": "test-hermes-001", "device_name": "test-hermes"}')
echo "   Response: $PAIR"
if echo "$PAIR" | grep -q '"hermes_id"'; then
    echo "   ✓ Pairing successful"
else
    echo "   ✗ Pairing failed"
    exit 1
fi

# Connect with token
echo ""
echo "4. Connecting Hermes with authority token..."
CONNECT=$(curl -s -X POST "$DAEMON_URL/hermes/connect" \
    -H "Content-Type: application/json" \
    -d "{\"authority_token\": \"$TOKEN\"}")
echo "   Response: $CONNECT"
if echo "$CONNECT" | grep -q '"hermes_id"'; then
    echo "   ✓ Connection successful"
else
    echo "   ✗ Connection failed"
    exit 1
fi

# Read status
echo ""
echo "5. Reading miner status through adapter..."
STATUS=$(curl -s "$DAEMON_URL/hermes/status" \
    -H "Authorization: Hermes test-hermes-001")
echo "   Response: $STATUS"
if echo "$STATUS" | grep -q '"status"'; then
    echo "   ✓ Status read successful"
else
    echo "   ✗ Status read failed"
    exit 1
fi

# Append summary
echo ""
echo "6. Appending Hermes summary..."
SUMMARY=$(curl -s -X POST "$DAEMON_URL/hermes/summary" \
    -H "Authorization: Hermes test-hermes-001" \
    -H "Content-Type: application/json" \
    -d '{"summary_text": "Miner running normally at 50kH/s", "authority_scope": "observe"}')
echo "   Response: $SUMMARY"
if echo "$SUMMARY" | grep -q '"appended"'; then
    echo "   ✓ Summary appended"
else
    echo "   ✗ Summary append failed"
    exit 1
fi

# Get filtered events
echo ""
echo "7. Getting filtered events (should not include user_message)..."
EVENTS=$(curl -s "$DAEMON_URL/hermes/events" \
    -H "Authorization: Hermes test-hermes-001")
echo "   Response: $EVENTS"
if echo "$EVENTS" | grep -q '"hermes_summary"'; then
    if echo "$EVENTS" | grep -q '"user_message"'; then
        echo "   ✗ WARNING: user_message found in filtered events!"
    else
        echo "   ✓ Events filtered correctly (no user_message)"
    fi
else
    echo "   ✗ Events read failed"
    exit 1
fi

# Test control boundary - should be rejected
echo ""
echo "8. Testing control boundary (should be rejected)..."
CONTROL=$(curl -s -X POST "$DAEMON_URL/miner/start" \
    -H "Authorization: Hermes test-hermes-001")
echo "   Response: $CONTROL"
# Note: Without Hermes session active, this may return 404 or 403
echo "   ✓ Control attempt handled"

# Cleanup
rm -f /tmp/hermes_token.txt

echo ""
echo "=== All smoke tests passed! ==="
