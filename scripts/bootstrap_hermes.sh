#!/bin/bash
#
# bootstrap_hermes.sh - Bootstrap Hermes adapter with Zend gateway
#
# This script:
# 1. Ensures daemon is running
# 2. Creates a Hermes pairing with observe+summarize capabilities
# 3. Proves the adapter can connect, read status, and append summaries
#
# Usage:
#   ./scripts/bootstrap_hermes.sh
#
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(dirname "$SCRIPT_DIR")"
DAEMON_DIR="$ROOT_DIR/services/home-miner-daemon"
ADAPTER_DIR="$ROOT_DIR/services/hermes-adapter"
STATE_DIR="$ROOT_DIR/state"

# Default daemon binding
BIND_HOST="${ZEND_BIND_HOST:-127.0.0.1}"
BIND_PORT="${ZEND_BIND_PORT:-8080}"
DAEMON_URL="http://$BIND_HOST:$BIND_PORT"

# PID file for daemon
PID_FILE="$STATE_DIR/daemon.pid"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

ensure_daemon() {
    # Check if daemon is already running
    if curl -s "$DAEMON_URL/health" > /dev/null 2>&1; then
        log_info "Daemon already running"
        return 0
    fi

    # Check for PID file
    if [ -f "$PID_FILE" ]; then
        PID=$(cat "$PID_FILE")
        if kill -0 "$PID" 2>/dev/null; then
            log_info "Daemon running (PID: $PID)"
            return 0
        fi
        rm -f "$PID_FILE"
    fi

    # Start daemon
    log_info "Starting daemon on $BIND_HOST:$BIND_PORT..."
    mkdir -p "$STATE_DIR"
    export ZEND_STATE_DIR="$STATE_DIR"
    export ZEND_BIND_HOST="$BIND_HOST"
    export ZEND_BIND_PORT="$BIND_PORT"

    cd "$DAEMON_DIR"
    python3 daemon.py &
    DAEMON_PID=$!
    echo "$DAEMON_PID" > "$PID_FILE"

    # Wait for daemon
    for i in {1..20}; do
        if curl -s "$DAEMON_URL/health" > /dev/null 2>&1; then
            log_info "Daemon ready"
            return 0
        fi
        sleep 0.25
    done

    log_error "Daemon failed to start"
    return 1
}

bootstrap_hermes() {
    log_info "Bootstrapping Hermes adapter..."

    # Create state directory for adapter
    mkdir -p "$STATE_DIR"

    # First ensure principal exists
    cd "$DAEMON_DIR"
    python3 -c "
import sys
sys.path.insert(0, '.')
from store import load_or_create_principal
principal = load_or_create_principal()
print(f'principal_id={principal.id}')
"

    # Run the adapter proof
    export ZEND_STATE_DIR="$STATE_DIR"
    export ZEND_DAEMON_URL="$DAEMON_URL"

    cd "$ADAPTER_DIR"
    python3 -c "
import sys
sys.path.insert(0, '.')
from adapter import HermesAdapter, HermesSummary

# Create adapter and connect with observe+summarize token
adapter = HermesAdapter()
conn = adapter.connect('hermes-gateway:observe,summarize')

print(f'connected=true')
print(f'device_name={conn.device_name}')
print(f'capabilities={conn.capabilities}')

# Read status (observe capability)
status = adapter.readStatus()
print(f'status_read=true')
print(f'miner_status={status.status}')

# Append a summary (summarize capability)
summary = HermesSummary(
    summary_text='Hermes adapter bootstrap: connection established successfully',
    authority_scope=adapter.getScope()
)
adapter.appendSummary(summary)
print(f'summary_appended=true')

# Verify scope
scope = adapter.getScope()
print(f'scope={scope}')
"

    local result=$?

    if [ $result -ne 0 ]; then
        log_error "Hermes adapter bootstrap failed"
        return 1
    fi

    log_info "Hermes adapter bootstrap complete"
    return 0
}

# Main
case "${1:-}" in
    "")
        ensure_daemon
        bootstrap_hermes
        ;;
    --daemon)
        ensure_daemon
        ;;
    *)
        echo "Usage: $0 [--daemon]"
        exit 1
        ;;
esac