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
DAEMON_URL="http://$BIND_HOST:$BIND_PORT"

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

daemon_reachable() {
    curl -sf "$DAEMON_URL/health" > /dev/null 2>&1
}

is_owned_daemon_pid() {
    local pid="$1"
    local cwd
    local cmdline

    [ -n "$pid" ] || return 1
    [ -d "/proc/$pid" ] || return 1

    cwd="$(readlink -f "/proc/$pid/cwd" 2>/dev/null || true)"
    cmdline="$(tr '\0' ' ' < "/proc/$pid/cmdline" 2>/dev/null || true)"

    [ "$cwd" = "$DAEMON_DIR" ] && [[ "$cmdline" == *"daemon.py"* ]]
}

stop_daemon() {
    if [ -f "$PID_FILE" ]; then
        PID=$(cat "$PID_FILE")
        if kill -0 "$PID" 2>/dev/null && is_owned_daemon_pid "$PID"; then
            log_info "Stopping daemon (PID: $PID)"
            kill "$PID" 2>/dev/null || true
            sleep 1
            # Force kill if still running
            kill -9 "$PID" 2>/dev/null || true
        elif [ -n "$PID" ]; then
            log_warn "Ignoring stale daemon pid file ($PID)"
        fi
        rm -f "$PID_FILE"
    fi
}

reset_state() {
    mkdir -p "$STATE_DIR"
    rm -f \
        "$STATE_DIR/principal.json" \
        "$STATE_DIR/pairing-store.json" \
        "$STATE_DIR/event-spine.jsonl" \
        "$STATE_DIR/miner-state.json"
}

start_daemon() {
    if daemon_reachable; then
        log_info "Daemon already reachable on $BIND_HOST:$BIND_PORT"
        return 0
    fi

    # Check if already running
    if [ -f "$PID_FILE" ]; then
        PID=$(cat "$PID_FILE" 2>/dev/null)
        if [ -n "$PID" ] && kill -0 "$PID" 2>/dev/null && is_owned_daemon_pid "$PID"; then
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
    export ZEND_DAEMON_URL="$DAEMON_URL"

    log_info "Starting Zend Home Miner Daemon on $BIND_HOST:$BIND_PORT..."

    # Start daemon in background
    cd "$DAEMON_DIR"
    python3 daemon.py &
    DAEMON_PID=$!

    echo "$DAEMON_PID" > "$PID_FILE"

    # Wait for daemon to be ready
    log_info "Waiting for daemon to start..."
    for i in {1..10}; do
        if daemon_reachable; then
            log_info "Daemon is ready"
            break
        fi
        sleep 0.5
    done

    # Verify daemon is running
    if daemon_reachable; then
        log_info "Daemon started (PID: $DAEMON_PID)"
        return 0
    fi

    if ! kill -0 "$DAEMON_PID" 2>/dev/null; then
        rm -f "$PID_FILE"
    fi

    log_warn "Daemon HTTP server unavailable; continuing with embedded CLI fallback"
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
        reset_state
        start_daemon
        bootstrap_principal
        ;;
    *)
        echo "Usage: $0 [--daemon|--stop|--status]"
        exit 1
        ;;
esac
