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

is_port_in_use() {
    local host="$1"
    local port="$2"
    if command -v ss &>/dev/null; then
        ss -tlnp 2>/dev/null | grep -q ":${port}[[:space:]]"
    elif command -v netstat &>/dev/null; then
        netstat -tlnp 2>/dev/null | grep -q ":${port}[[:space:]]"
    else
        # Fallback: try to connect
        timeout 1 bash -c "echo >/dev/tcp/$host/$port" 2>/dev/null
        return $?
    fi
}

start_daemon() {
    # Check if port is already in use (covers stale daemon crashes)
    if is_port_in_use "$BIND_HOST" "$BIND_PORT"; then
        log_warn "Port $BIND_PORT already in use, checking for stale process..."
        # Try to find and kill any python daemon holding this port
        if command -v fuser &>/dev/null; then
            fuser -k "${BIND_PORT}/tcp" 2>/dev/null || true
            sleep 1
        fi
        # If still in use, give up
        if is_port_in_use "$BIND_HOST" "$BIND_PORT"; then
            log_error "Port $BIND_PORT still in use after cleanup"
            return 1
        fi
    fi

    # Check if PID file points to live process
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

    # Run bootstrap via CLI
    cd "$DAEMON_DIR"
    OUTPUT=$(python3 cli.py bootstrap --device "${DEVICE_NAME:-alice-phone}" 2>&1)

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
