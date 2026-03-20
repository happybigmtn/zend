#!/bin/bash
#
# bootstrap_hermes.sh - Bootstrap the Zend Hermes Adapter
#
# This script:
# 1. Ensures the home-miner daemon is running
# 2. Creates a Hermes authority token with observe+summarize capabilities
# 3. Verifies the adapter can connect and exercise granted capabilities
#
# Usage:
#   ./scripts/bootstrap_hermes.sh
#
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(dirname "$SCRIPT_DIR")"
DAEMON_DIR="$ROOT_DIR/services/home-miner-daemon"
ADAPTER_DIR="$ROOT_DIR/services/hermes-adapter"
STATE_DIR="${ZEND_STATE_DIR:-$ROOT_DIR/state}"

# Default to development binding
BIND_HOST="${ZEND_BIND_HOST:-127.0.0.1}"
BIND_PORT="${ZEND_BIND_PORT:-8080}"
GATEWAY_URL="${ZEND_GATEWAY_URL:-http://$BIND_HOST:$BIND_PORT}"

export ZEND_STATE_DIR="$STATE_DIR"
export ZEND_BIND_HOST="$BIND_HOST"
export ZEND_BIND_PORT="$BIND_PORT"
export ZEND_GATEWAY_URL="$GATEWAY_URL"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

log_info() {
    echo -e "${GREEN}[INFO]${NC} $1" >&2
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1" >&2
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1" >&2
}

# Check if daemon is running
check_daemon() {
    if curl -s "$GATEWAY_URL/health" > /dev/null 2>&1; then
        return 0
    fi
    return 1
}

# Start daemon if needed
start_daemon_if_needed() {
    if check_daemon; then
        log_info "Daemon already running on $GATEWAY_URL"
        return 0
    fi

    log_info "Starting home-miner daemon..."

    # Ensure state directory exists
    mkdir -p "$STATE_DIR"

    # Start daemon in background
    cd "$DAEMON_DIR"
    python3 daemon.py &
    DAEMON_PID=$!

    # Wait for daemon to be ready
    log_info "Waiting for daemon to start..."
    for i in {1..10}; do
        if curl -s "$GATEWAY_URL/health" > /dev/null 2>&1; then
            log_info "Daemon is ready"
            return 0
        fi
        sleep 0.5
    done

    log_error "Daemon failed to start"
    return 1
}

# Create Hermes authority token
create_hermes_token() {
    log_info "Creating Hermes authority token..."

    cd "$ADAPTER_DIR"

    # Generate token with observe and summarize capabilities
    TOKEN=$(python3 -c "
import sys
import os
sys.path.insert(0, '.')
from authority import encode_authority_token, save_hermes_token
sys.path.insert(0, '$DAEMON_DIR')
from store import load_or_create_principal

principal = load_or_create_principal()
token = encode_authority_token(
    principal_id=principal.id,
    capabilities=['observe', 'summarize']
)
save_hermes_token(token)
print(token)
")

    if [ -z "$TOKEN" ]; then
        log_error "Failed to create Hermes token"
        return 1
    fi

    log_info "Hermes token created"
    echo "$TOKEN"
}

# Verify observe capability
verify_observe() {
    local TOKEN="$1"
    log_info "Verifying observe capability..."

    cd "$ADAPTER_DIR"

    python3 -c "
import sys
sys.path.insert(0, '.')
from adapter import HermesAdapter

adapter = HermesAdapter(gateway_url='$GATEWAY_URL')
adapter.connect('$TOKEN')
status = adapter.readStatus()
print(f'Observe: status={status.status}, mode={status.mode}')
"

    if [ $? -eq 0 ]; then
        log_info "Observe capability verified"
        return 0
    else
        log_error "Observe capability check failed"
        return 1
    fi
}

# Verify summarize capability
verify_summarize() {
    local TOKEN="$1"
    log_info "Verifying summarize capability..."

    cd "$ADAPTER_DIR"

    python3 -c "
import sys
sys.path.insert(0, '.')
from adapter import HermesAdapter, HermesSummary

adapter = HermesAdapter(gateway_url='$GATEWAY_URL')
adapter.connect('$TOKEN')
summary = HermesSummary(
    summary_text='Bootstrap verification: Hermes adapter initialized successfully',
    authority_scope=['observe', 'summarize']
)
adapter.appendSummary(summary)
print('Summarize: summary appended to event spine')
"

    if [ $? -eq 0 ]; then
        log_info "Summarize capability verified"
        return 0
    else
        log_error "Summarize capability check failed"
        return 1
    fi
}

# Main
main() {
    log_info "Bootstrapping Zend Hermes Adapter..."
    echo ""

    # Start daemon if needed
    start_daemon_if_needed || exit 1
    echo ""

    # Create Hermes token
    TOKEN=$(create_hermes_token)
    if [ $? -ne 0 ] || [ -z "$TOKEN" ]; then
        exit 1
    fi
    echo ""

    # Verify capabilities
    verify_observe "$TOKEN" || exit 1
    echo ""

    verify_summarize "$TOKEN" || exit 1
    echo ""

    log_info "Hermes Adapter bootstrap complete"
    echo ""
    echo "Summary:"
    echo "  - Daemon: running on $GATEWAY_URL"
    echo "  - Capabilities: observe, summarize"
    echo "  - Token: [saved to state]"
    echo ""

    return 0
}

main "$@"
