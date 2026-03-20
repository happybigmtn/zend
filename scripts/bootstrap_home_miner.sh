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

# Canonical binding for this slice: always 8080 regardless of environment.
# The preflight harness expects port 8080 in its curl commands.
BIND_HOST="127.0.0.1"
BIND_PORT="8080"

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
    if [ -f "$PID_FILE" ]; then
        PID=$(cat "$PID_FILE")
        if kill -0 "$PID" 2>/dev/null; then
            log_info "Stopping daemon (PID: $PID)"
            kill "$PID" 2>/dev/null || true
            sleep 1
            # Force kill if still running
            kill -9 "$PID" 2>/dev/null || true
        fi
        rm -f "$PID_FILE"
    fi
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
    log_info "Bootstrapping principal identity..."

    # Run bootstrap via CLI; capture both stdout and exit code.
    # Disable set -e locally since we handle non-zero exits explicitly.
    cd "$DAEMON_DIR"
    set +e
    OUTPUT=$(python3 cli.py bootstrap --device "${DEVICE_NAME:-alice-phone}" 2>&1)
    RESULT=$?
    set -e

    # Print output regardless of outcome
    echo "$OUTPUT"

    if [ $RESULT -eq 0 ]; then
        log_info "Bootstrap complete"
        return 0
    else
        # Idempotent case: device already paired is treated as success
        if echo "$OUTPUT" | grep -q "already paired"; then
            log_info "Bootstrap idempotent — device already paired"
            return 0
        fi
        log_error "Bootstrap failed"
        return 1
    fi
}

show_status() {
    log_info "Miner status:"
    cd "$DAEMON_DIR"
    python3 cli.py status 2>/dev/null || echo "  (daemon not responding)"
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
        # Default: start daemon and bootstrap
        stop_daemon
        start_daemon
        bootstrap_principal
        ;;
    *)
        echo "Usage: $0 [--daemon|--stop|--status]"
        exit 1
        ;;
esac
