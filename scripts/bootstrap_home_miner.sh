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

start_daemon() {
    # Kill any process already listening on the target port (stale daemon from prior runs)
    log_info "Checking for stale daemon on $BIND_HOST:$BIND_PORT..."
    STALE_PIDS=$(ss -tlnp "sport = :$BIND_PORT" 2>/dev/null | grep -oP 'pid=\K[0-9]+' | sort -u)
    if [ -n "$STALE_PIDS" ]; then
        for SPID in $STALE_PIDS; do
            log_warn "Killing stale daemon (PID: $SPID) on port $BIND_PORT"
            kill "$SPID" 2>/dev/null || true
        done
        sleep 1
        # Force kill any that survived
        for SPID in $STALE_PIDS; do
            kill -9 "$SPID" 2>/dev/null || true
        done
        sleep 1
    fi

    # Check PID file for tracked daemon
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

    # Wait for daemon to be ready — poll health endpoint until it responds
    log_info "Waiting for daemon to start..."
    DAEMON_READY=no
    for i in {1..20}; do
        if curl -s "http://$BIND_HOST:$BIND_PORT/health" > /dev/null 2>&1; then
            DAEMON_READY=yes
            log_info "Daemon is ready"
            break
        fi
        # Also check the process didn't die immediately
        if ! kill -0 "$DAEMON_PID" 2>/dev/null; then
            log_error "Daemon process died during startup"
            return 1
        fi
        sleep 0.5
    done

    if [ "$DAEMON_READY" != "yes" ]; then
        log_error "Daemon failed to start (port $BIND_PORT not responding)"
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
        PAIRING_TOKEN=$(echo "$OUTPUT" | python3 -c "import sys,json; print(json.load(sys.stdin).get('pairing_token', ''))" 2>/dev/null || echo "")
        DEVICE_NAME_OUT=$(echo "$OUTPUT" | python3 -c "import sys,json; print(json.load(sys.stdin).get('device_name', '${DEVICE_NAME:-alice-phone}'))" 2>/dev/null || echo "${DEVICE_NAME:-alice-phone}")
        if [ -n "$PAIRING_TOKEN" ]; then
            echo ""
            echo "pairing_token=$PAIRING_TOKEN"
            echo "paired $DEVICE_NAME_OUT"
        fi
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
    python3 cli.py status --client "${DEVICE_NAME:-alice-phone}" 2>/dev/null || echo "  (daemon not responding)"
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
