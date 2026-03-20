#!/bin/bash
#
# bootstrap_hermes.sh - Bootstrap Hermes adapter for Zend Home Miner
#
# This script:
# 1. Starts the local home-miner daemon
# 2. Creates a Hermes authority token for testing
#
# Usage:
#   ./scripts/bootstrap_hermes.sh [--daemon]
#   ./scripts/bootstrap_hermes.sh --stop
#
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(dirname "$SCRIPT_DIR")"
DAEMON_DIR="$ROOT_DIR/services/home-miner-daemon"
STATE_DIR="${ZEND_STATE_DIR:-$ROOT_DIR/state}"

# Default to development binding
BIND_HOST="${ZEND_BIND_HOST:-127.0.0.1}"
BIND_PORT="${ZEND_BIND_PORT:-8080}"
STARTUP_RETRIES="${ZEND_STARTUP_RETRIES:-10}"
STARTUP_INTERVAL_SECONDS="${ZEND_STARTUP_INTERVAL_SECONDS:-0.5}"
DAEMON_PYTHON="${ZEND_DAEMON_PYTHON:-python3}"

# PID file
PID_FILE="$STATE_DIR/daemon.pid"
DAEMON_LOG_FILE="$STATE_DIR/hermes-daemon.log"

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

process_is_running() {
    local pid="$1"
    local status=""

    if ! kill -0 "$pid" 2>/dev/null; then
        return 1
    fi

    status="$(ps -o stat= -p "$pid" 2>/dev/null | tr -d '[:space:]')"
    if [[ -z "$status" || "$status" == Z* ]]; then
        return 1
    fi

    return 0
}

report_start_failure() {
    local reason="$1"

    rm -f "$PID_FILE"

    log_error "GatewayUnavailable: failed to start Zend Home Miner daemon"
    echo "error_code=GATEWAY_UNAVAILABLE"
    echo "reason=$reason"

    if [ -f "$DAEMON_LOG_FILE" ]; then
        echo "daemon_log=$DAEMON_LOG_FILE"
        if grep -q "Address already in use" "$DAEMON_LOG_FILE"; then
            echo "detail=DAEMON_PORT_IN_USE"
        fi
    fi
}

stop_daemon() {
    if [ -f "$PID_FILE" ]; then
        PID=$(cat "$PID_FILE")
        if process_is_running "$PID"; then
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
        if [ -n "$PID" ] && process_is_running "$PID"; then
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

    : > "$DAEMON_LOG_FILE"

    # Start daemon in background
    cd "$DAEMON_DIR"
    PYTHONUNBUFFERED=1 "$DAEMON_PYTHON" daemon.py >"$DAEMON_LOG_FILE" 2>&1 &
    DAEMON_PID=$!

    echo "$DAEMON_PID" > "$PID_FILE"

    # Wait for daemon to be ready
    log_info "Waiting for daemon to start..."
    attempt=1
    while [ "$attempt" -le "$STARTUP_RETRIES" ]; do
        if curl -s "http://$BIND_HOST:$BIND_PORT/health" > /dev/null 2>&1 && process_is_running "$DAEMON_PID"; then
            log_info "Daemon is ready"
            break
        fi

        if ! process_is_running "$DAEMON_PID"; then
            wait "$DAEMON_PID" 2>/dev/null || true
            report_start_failure "daemon_process_exited"
            return 1
        fi

        if [ "$attempt" -lt "$STARTUP_RETRIES" ]; then
            sleep "$STARTUP_INTERVAL_SECONDS"
        fi
        attempt=$((attempt + 1))
    done

    if ! curl -s "http://$BIND_HOST:$BIND_PORT/health" > /dev/null 2>&1; then
        kill "$DAEMON_PID" 2>/dev/null || true
        wait "$DAEMON_PID" 2>/dev/null || true
        report_start_failure "daemon_healthcheck_timeout"
        return 1
    fi

    log_info "Daemon started (PID: $DAEMON_PID)"
    return 0
}

bootstrap_hermes_token() {
    log_info "Bootstrapping Hermes authority token..."

    cd "$DAEMON_DIR"

    # Create a Hermes token with both observe and summarize capabilities
    set +e
    OUTPUT=$(python3 -c "
import sys
sys.path.insert(0, '.')
from adapter import create_hermes_token

token, encoded = create_hermes_token(
    principal_id='test-hermes-principal',
    capabilities=['observe', 'summarize']
)
print(f'token={token}')
print(f'principal_id=test-hermes-principal')
print(f'capabilities=observe,summarize')
" 2>&1)
    RESULT=$?
    set -e

    if [ $RESULT -eq 0 ]; then
        echo "$OUTPUT"
        log_info "Hermes token bootstrap complete"
        return 0
    else
        log_error "Hermes token bootstrap failed: $OUTPUT"
        return 1
    fi
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
    "")
        # Default: start daemon and bootstrap Hermes token
        stop_daemon
        start_daemon
        bootstrap_hermes_token
        ;;
    *)
        echo "Usage: $0 [--daemon|--stop]"
        exit 1
        ;;
esac
