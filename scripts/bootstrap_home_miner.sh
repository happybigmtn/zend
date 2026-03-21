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
STATE_DIR="${ZEND_STATE_DIR:-$ROOT_DIR/state}"
BOOTSTRAP_HELPER="$DAEMON_DIR/bootstrap_runtime.py"

# Default to development binding
BIND_HOST="${ZEND_BIND_HOST:-127.0.0.1}"
BIND_PORT="${ZEND_BIND_PORT:-8080}"

# PID file
PID_FILE="$STATE_DIR/daemon.pid"
LOG_FILE="${ZEND_DAEMON_LOG_FILE:-$STATE_DIR/daemon.log}"

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

pid_is_active() {
    python3 "$BOOTSTRAP_HELPER" pid-active "$1"
}

owned_listener_pid() {
    python3 "$BOOTSTRAP_HELPER" owned-listener-pid "$BIND_HOST" "$BIND_PORT" "$DAEMON_DIR"
}

managed_listener_pids() {
    python3 "$BOOTSTRAP_HELPER" managed-listener-pids "$BIND_HOST" "$BIND_PORT" "$DAEMON_DIR"
}

listener_report() {
    python3 "$BOOTSTRAP_HELPER" listener-report "$BIND_HOST" "$BIND_PORT" "$DAEMON_DIR"
}

healthcheck_daemon() {
    python3 - "$BIND_HOST" "$BIND_PORT" <<'PY'
import json
import sys
import urllib.error
import urllib.request

url = f"http://{sys.argv[1]}:{sys.argv[2]}/health"

try:
    with urllib.request.urlopen(url, timeout=0.25) as response:
        if response.status != 200:
            raise RuntimeError(f"unexpected_status={response.status}")
        json.load(response)
except Exception:
    raise SystemExit(1)
PY
}

kill_pid() {
    local pid="$1"

    if [ -z "$pid" ]; then
        return 0
    fi

    if ! pid_is_active "$pid"; then
        return 0
    fi

    kill "$pid" 2>/dev/null || true
    for _ in {1..10}; do
        if ! pid_is_active "$pid"; then
            return 0
        fi
        sleep 0.2
    done

    kill -9 "$pid" 2>/dev/null || true
    for _ in {1..10}; do
        if ! pid_is_active "$pid"; then
            return 0
        fi
        sleep 0.1
    done

    return 1
}

reclaim_managed_listeners() {
    local log_prefix="$1"
    local skip_pid="${2:-}"
    local managed_pids=""
    local listener_pid=""

    if ! managed_pids=$(managed_listener_pids 2>/dev/null); then
        return 0
    fi

    while IFS= read -r listener_pid; do
        if [ -z "$listener_pid" ]; then
            continue
        fi
        if [ -n "$skip_pid" ] && [ "$listener_pid" = "$skip_pid" ]; then
            continue
        fi

        log_warn "$log_prefix on $BIND_HOST:$BIND_PORT (PID: $listener_pid)"
        kill_pid "$listener_pid"
    done <<< "$managed_pids"
}

log_daemon_output() {
    if [ -f "$LOG_FILE" ] && [ -s "$LOG_FILE" ]; then
        tail -n 20 "$LOG_FILE" >&2 || true
    fi
}

stop_daemon() {
    local pid=""

    if [ -f "$PID_FILE" ]; then
        pid=$(cat "$PID_FILE" 2>/dev/null || true)
        if [ -n "$pid" ] && pid_is_active "$pid"; then
            log_info "Stopping daemon (PID: $pid)"
            kill_pid "$pid"
        fi
        rm -f "$PID_FILE"
    fi

    reclaim_managed_listeners "Stopping stale daemon listener" "$pid"
}

start_daemon() {
    local listener_report_json=""
    local foreign_pid=""
    local foreign_cmd=""
    local existing_pid=""

    # Check if already running
    if [ -f "$PID_FILE" ]; then
        existing_pid=$(cat "$PID_FILE" 2>/dev/null || true)
        if [ -n "$existing_pid" ] && pid_is_active "$existing_pid"; then
            log_warn "Daemon already running (PID: $existing_pid)"
            return 0
        fi
        rm -f "$PID_FILE"
    fi

    reclaim_managed_listeners "Reclaiming stale Zend daemon listener" "$existing_pid"

    # Ensure state directory exists
    mkdir -p "$STATE_DIR"
    : > "$LOG_FILE"

    # Set environment
    export ZEND_STATE_DIR="$STATE_DIR"
    export ZEND_BIND_HOST="$BIND_HOST"
    export ZEND_BIND_PORT="$BIND_PORT"
    export ZEND_DAEMON_LOG_FILE="$LOG_FILE"

    listener_report_json="$(listener_report)"
    foreign_pid="$(printf '%s' "$listener_report_json" | python3 -c "import json,sys; listeners=json.load(sys.stdin)['listeners']; foreign=next((item for item in listeners if not item.get('managed')), None); print('' if foreign is None else foreign['pid'])")"
    foreign_cmd="$(printf '%s' "$listener_report_json" | python3 -c "import json,sys; listeners=json.load(sys.stdin)['listeners']; foreign=next((item for item in listeners if not item.get('managed')), None); print('' if foreign is None else foreign['cmdline'])")"
    if [ -n "$foreign_pid" ]; then
        log_error "GatewayUnavailable (DAEMON_PORT_IN_USE): $BIND_HOST:$BIND_PORT is already owned by PID $foreign_pid"
        if [ -n "$foreign_cmd" ]; then
            log_error "Conflicting command: $foreign_cmd"
        fi
        log_error "Recovery: stop the conflicting process or run ./scripts/bootstrap_home_miner.sh --stop if it is a stale Zend daemon"
        return 1
    fi

    log_info "Starting Zend Home Miner Daemon on $BIND_HOST:$BIND_PORT..."

    # Start daemon in background
    cd "$DAEMON_DIR"
    python3 daemon.py > "$LOG_FILE" 2>&1 &
    DAEMON_PID=$!

    echo "$DAEMON_PID" > "$PID_FILE"

    # Wait for daemon to be ready
    log_info "Waiting for daemon to start..."
    local ready=0
    for i in {1..10}; do
        if ! pid_is_active "$DAEMON_PID"; then
            log_error "Daemon failed to start"
            log_daemon_output
            rm -f "$PID_FILE"
            return 1
        fi
        if healthcheck_daemon; then
            log_info "Daemon is ready"
            ready=1
            break
        fi
        sleep 0.5
    done

    if [ "$ready" -ne 1 ]; then
        log_error "GatewayUnavailable: daemon did not become ready on $BIND_HOST:$BIND_PORT"
        log_daemon_output
        kill_pid "$DAEMON_PID"
        rm -f "$PID_FILE"
        return 1
    fi

    log_info "Daemon started (PID: $DAEMON_PID)"
    return 0
}

bootstrap_principal() {
    log_info "Bootstrapping principal identity..."

    # Run bootstrap via CLI
    cd "$DAEMON_DIR"
    set +e
    OUTPUT=$(python3 cli.py bootstrap --device "${DEVICE_NAME:-alice-phone}" 2>&1)
    RESULT=$?
    set -e

    if [ $RESULT -eq 0 ]; then
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
