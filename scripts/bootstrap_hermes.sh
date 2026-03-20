#!/bin/bash
#
# bootstrap_hermes.sh - Bootstrap the Hermes adapter service
#
# Usage:
#   ./scripts/bootstrap_hermes.sh
#
# This script:
# 1. Initializes Hermes adapter state
# 2. Creates a principal if one doesn't exist
# 3. Proves the adapter can connect and append a summary
#
set +e  # Don't exit on error - we handle errors explicitly

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(dirname "$SCRIPT_DIR")"
ADAPTER_DIR="$ROOT_DIR/services/hermes-adapter"
STATE_DIR="$ROOT_DIR/state"

# Ensure state directory exists
mkdir -p "$STATE_DIR"

# Set state directory for Python modules
export ZEND_STATE_DIR="$STATE_DIR"

echo "Bootstrapping Hermes adapter..."

# Test 1: Verify adapter module can be imported
echo "Test 1: Verifying adapter module..."
cd "$ADAPTER_DIR"
python3 -c "
import sys
sys.path.insert(0, '.')
sys.path.insert(0, '$ROOT_DIR/services/home-miner-daemon')
from adapter import HermesAdapter
print('  adapter module: OK')
" 2>&1
if [ $? -ne 0 ]; then
    echo "FAIL: adapter module import failed"
    exit 1
fi

# Test 2: Create adapter and connect
echo "Test 2: Connecting adapter with delegated authority..."
CONNECTION_RESULT=$(python3 -c "
import sys
sys.path.insert(0, '.')
sys.path.insert(0, '$ROOT_DIR/services/home-miner-daemon')
from adapter import HermesAdapter

adapter = HermesAdapter()
conn = adapter.connect('hermes-authority-token-milestone-1')
print(f'connection_id={conn.connection_id}')
print(f'principal_id={conn.principal_id}')
print(f'capabilities={chr(44).join(conn.capabilities)}')
" 2>&1)
if [ $? -ne 0 ]; then
    echo "FAIL: adapter connection failed"
    echo "$CONNECTION_RESULT"
    exit 1
fi
echo "  connection: OK"

# Extract principal_id for next test
PRINCIPAL_ID=$(echo "$CONNECTION_RESULT" | grep principal_id= | cut -d= -f2)
echo "  principal_id: $PRINCIPAL_ID"

# Test 3: Read status (requires observe capability)
echo "Test 3: Reading status (observe capability)..."
python3 -c "
import sys
sys.path.insert(0, '.')
sys.path.insert(0, '$ROOT_DIR/services/home-miner-daemon')
from adapter import HermesAdapter

adapter = HermesAdapter()
adapter.connect('hermes-authority-token-milestone-1')
status = adapter.read_status()
print(f'  status: {status.get(\"status\", \"unknown\")}')
print('  observe capability: OK')
" 2>&1
if [ $? -ne 0 ]; then
    echo "FAIL: status read failed"
    exit 1
fi

# Test 4: Append summary (requires summarize capability)
echo "Test 4: Appending Hermes summary..."
SUMMARY_RESULT=$(python3 -c "
import sys
sys.path.insert(0, '.')
sys.path.insert(0, '$ROOT_DIR/services/home-miner-daemon')
from adapter import HermesAdapter

adapter = HermesAdapter()
adapter.connect('hermes-authority-token-milestone-1')
result = adapter.append_summary('Bootstrap test summary: Hermes adapter is operational')
print(f'event_id={result[\"event_id\"]}')
" 2>&1)
if [ $? -ne 0 ]; then
    echo "FAIL: summary append failed"
    echo "$SUMMARY_RESULT"
    exit 1
fi
echo "  summary append: OK"

# Test 5: Verify scope
echo "Test 5: Verifying authority scope..."
python3 -c "
import sys
sys.path.insert(0, '.')
sys.path.insert(0, '$ROOT_DIR/services/home-miner-daemon')
from adapter import HermesAdapter

adapter = HermesAdapter()
adapter.connect('hermes-authority-token-milestone-1')
scope = adapter.get_scope()
if 'observe' in scope and 'summarize' in scope:
    print('  scope: observe, summarize')
    print('  scope verification: OK')
else:
    print('FAIL: unexpected scope')
    sys.exit(1)
" 2>&1
if [ $? -ne 0 ]; then
    echo "FAIL: scope verification failed"
    exit 1
fi

echo ""
echo "Bootstrap complete: Hermes adapter is operational"
echo "principal_id=$PRINCIPAL_ID"

exit 0