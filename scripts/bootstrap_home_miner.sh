#!/bin/bash
#
# bootstrap_home_miner.sh - Bootstrap the Zend Home Miner daemon
#
# This script:
# 1. Starts the local home-miner daemon
# 2. Creates deterministic principal state
# 3. Emits a pairing bundle for a default client
#
# Usage:
#   ./scripts/bootstrap_home_miner.sh [--daemon]
#   ./scripts/bootstrap_home_miner.sh --stop
#
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(dirname "$SCRIPT_DIR")"
DAEMON_DIR="$ROOT_DIR/services/home-miner-daemon"
STATE_DIR="$ROOT_DIR/state"

# Default to development binding
BIND_HOST="${ZEND_BIND_HOST:-127.0.0.1}"
BIND_PORT="${ZEND_BIND_PORT:-8080}"

# PID file
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

stop_daemon() {
    # Kill by PID file first
    if [ -f "$PID_FILE" ]; then
        PID=$(cat "$PID_FILE")
        if [ -n "$PID" ] && kill -0 "$PID" 2>/dev/null; then
            log_info "Stopping daemon (PID: $PID)"
            kill "$PID" 2>/dev/null || true
            sleep 1
            kill -9 "$PID" 2>/dev/null || true
        fi
        rm -f "$PID_FILE"
    fi

    # Always ensure the port is actually free — handles daemons started outside this script
    if command -v fuser >/dev/null 2>&1; then
        fuser -k "$BIND_PORT/tcp" 2>/dev/null || true
    else
        # Fallback: find and kill the process holding the port
        PID_HOLDING=$(ss -tlnp 2>/dev/null | grep ":$BIND_PORT " | sed -n 's/.*pid=\([0-9]*\).*/\1/p' | head -1)
        if [ -n "$PID_HOLDING" ]; then
            log_info "Killing process $PID_HOLDING holding port $BIND_PORT"
            kill "$PID_HOLDING" 2>/dev/null || true
            sleep 1
            kill -9 "$PID_HOLDING" 2>/dev/null || true
        fi
    fi

    # Give the port a moment to be released
    sleep 1
}

start_daemon() {
    # Check if already running
    if [ -f "$PID_FILE" ]; then
        PID=$(cat "$PID_FILE" 2>/dev/null)
        if [ -n "$PID" ] && kill -0 "$PID" 2>/dev/null; then
            log_warn "Daemon already running (PID: $PID)"
            return 0
        fi
        rm -f "$PID_FILE"
    fi

    # Double-check the port is free (handles race with stop_daemon)
    if ss -tlnp 2>/dev/null | grep -q ":$BIND_PORT "; then
        log_error "Port $BIND_PORT is still in use — cannot start daemon"
        return 1
    fi

    # Ensure state directory exists
    mkdir -p "$STATE_DIR"

    # Set environment
    export ZEND_STATE_DIR="$STATE_DIR"
    export ZEND_BIND_HOST="$BIND_HOST"
    export ZEND_BIND_PORT="$BIND_PORT"

    log_info "Starting Zend Home Miner Daemon on $BIND_HOST:$BIND_PORT..."

    # Start daemon in background
    cd "$DAEMON_DIR"
    python3 daemon.py &
    DAEMON_PID=$!

    echo "$DAEMON_PID" > "$PID_FILE"

    # Wait for daemon to be ready
    log_info "Waiting for daemon to start..."
    for i in {1..10}; do
        if curl -s "http://$BIND_HOST:$BIND_PORT/health" > /dev/null 2>&1; then
            log_info "Daemon is ready"
            break
        fi
        sleep 0.5
    done

    # Verify daemon is running
    if ! kill -0 "$DAEMON_PID" 2>/dev/null; then
        log_error "Daemon failed to start"
        return 1
    fi

    log_info "Daemon started (PID: $DAEMON_PID)"
    return 0
}

bootstrap_principal() {
    local DEVICE="${DEVICE_NAME:-alice-phone}"
    log_info "Bootstrapping principal identity for device: $DEVICE..."

    # Set up environment for CLI
    export ZEND_STATE_DIR="$STATE_DIR"
    cd "$DAEMON_DIR"

    # Check if device is already paired (idempotency)
    EXISTING=$(python3 -c "
import sys, json
sys.path.insert(0, '.')
from store import get_pairing_by_device
p = get_pairing_by_device('$DEVICE')
if p:
    print(json.dumps({'device_name': p.device_name, 'capabilities': p.capabilities, 'paired_at': p.paired_at}))
else:
    print('{}')
" 2>&1)

    if [ -n "$EXISTING" ] && [ "$EXISTING" != "{}" ]; then
        log_info "Device '$DEVICE' already paired — skipping bootstrap (idempotent)"
        echo "$EXISTING"
        return 0
    fi

    # Run bootstrap via CLI
    OUTPUT=$(python3 cli.py bootstrap --device "$DEVICE" 2>&1)

    if [ $? -eq 0 ]; then
        echo "$OUTPUT"
        log_info "Bootstrap complete"
        return 0
    else
        log_error "Bootstrap failed: $OUTPUT"
        return 1
    fi
}

show_status() {
    log_info "Miner status:"
    cd "$DAEMON_DIR"
    python3 cli.py status 2>/dev/null || echo "  (daemon not responding)"
}

# Check if daemon is already reachable (may have been started outside this script)
daemon_is_reachable() {
    curl -s --fail "http://$BIND_HOST:$BIND_PORT/health" > /dev/null 2>&1
}

# Parse arguments
case "${1:-}" in
    --stop)
        log_info "Stopping Zend Home Miner Daemon"
        stop_daemon
        exit 0
        ;;
    --daemon)
        start_daemon
        exit $?
        ;;
    --status)
        show_status
        exit 0
        ;;
    "")
        # Default: ensure daemon is up, then bootstrap
        if daemon_is_reachable; then
            log_warn "Daemon already reachable on $BIND_HOST:$BIND_PORT — using existing instance"
        else
            stop_daemon
            if ! start_daemon; then
                log_error "Could not start daemon"
                exit 1
            fi
        fi
        bootstrap_principal
        ;;
    *)
        echo "Usage: $0 [--daemon|--stop|--status]"
        exit 1
        ;;
esac
