#!/bin/bash
#
# bootstrap_hermes.sh - Bootstrap the Hermes adapter for Zend Home
#
# This script:
# 1. Ensures the daemon is running
# 2. Creates Hermes adapter state with delegated observe authority
# 3. Verifies Hermes can append a summary to the event spine
#
# Hermes milestone 1 authority: observe-only + summary append.
# Direct miner control through Hermes is deferred.
#
# Usage:
#   ./scripts/bootstrap_hermes.sh
#   ./scripts/bootstrap_hermes.sh --stop
#
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(dirname "$SCRIPT_DIR")"
DAEMON_DIR="$ROOT_DIR/services/home-miner-daemon"
STATE_DIR="$ROOT_DIR/state"

# Daemon defaults
BIND_HOST="${ZEND_BIND_HOST:-127.0.0.1}"
BIND_PORT="${ZEND_BIND_PORT:-8080}"
DAEMON_URL="http://${BIND_HOST}:${BIND_PORT}"

# Hermes adapter state
HERMES_STATE_DIR="$STATE_DIR/hermes"
HERMES_PRINCIPAL_FILE="$HERMES_STATE_DIR/principal.json"

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

is_daemon_running() {
    if [ -f "$PID_FILE" ]; then
        PID=$(cat "$PID_FILE" 2>/dev/null)
        if [ -n "$PID" ] && kill -0 "$PID" 2>/dev/null; then
            return 0
        fi
    fi
    return 1
}

wait_for_daemon() {
    log_info "Waiting for daemon at $DAEMON_URL..."
    for i in {1..20}; do
        if curl -s "$DAEMON_URL/health" > /dev/null 2>&1; then
            log_info "Daemon is ready"
            return 0
        fi
        sleep 0.3
    done
    log_error "Daemon not responding"
    return 1
}

start_daemon_if_needed() {
    if is_daemon_running; then
        log_info "Daemon already running"
        wait_for_daemon
        return 0
    fi

    log_info "Daemon not running, starting..."
    mkdir -p "$STATE_DIR"

    export ZEND_STATE_DIR="$STATE_DIR"
    export ZEND_BIND_HOST="$BIND_HOST"
    export ZEND_BIND_PORT="$BIND_PORT"

    cd "$DAEMON_DIR"
    python3 daemon.py &
    DAEMON_PID=$!
    echo "$DAEMON_PID" > "$PID_FILE"

    wait_for_daemon
    log_info "Daemon started (PID: $DAEMON_PID)"
    return 0
}

create_hermes_state() {
    log_info "Creating Hermes adapter state..."

    mkdir -p "$HERMES_STATE_DIR"

    # Create Hermes principal with observe-only delegated authority
    # This is the minimal Hermes identity for milestone 1
    cat > "$HERMES_PRINCIPAL_FILE" << 'EOF'
{
  "principal_id": "hermes-adapter-001",
  "name": "Hermes Gateway Adapter",
  "capabilities": ["observe"],
  "authority_scope": ["observe"],
  "summary_append_enabled": true,
  "created_at": "2026-03-20T00:00:00Z",
  "milestone": 1,
  "note": "Hermes milestone 1: observe-only + summary append. Direct control deferred."
}
EOF

    log_info "Hermes state created at $HERMES_PRINCIPAL_FILE"
    return 0
}

verify_hermes_connection() {
    log_info "Verifying Hermes adapter connection..."

    # Verify daemon health
    HEALTH=$(curl -s "$DAEMON_URL/health")
    if [ $? -ne 0 ]; then
        log_error "Cannot reach daemon"
        return 1
    fi

    # Verify Hermes state exists
    if [ ! -f "$HERMES_PRINCIPAL_FILE" ]; then
        log_error "Hermes state not found"
        return 1
    fi

    # Test summary append via hermes_summary_smoke pattern
    cd "$DAEMON_DIR"
    SUMMARY_OUTPUT=$(python3 -c "
import sys
sys.path.insert(0, '.')
from store import load_or_create_principal
from spine import append_hermes_summary

# Use the Hermes principal
hermes_principal_id = 'hermes-adapter-001'
event = append_hermes_summary(
    'Hermes adapter bootstrap verification',
    ['observe'],
    hermes_principal_id
)
print(f'verification_event_id={event.id}')
print(f'hermes_principal_id={hermes_principal_id}')
" 2>&1)

    if [ $? -eq 0 ]; then
        log_info "Hermes summary append verified"
        echo "$SUMMARY_OUTPUT"
        return 0
    else
        log_error "Hermes summary append failed"
        echo "$SUMMARY_OUTPUT"
        return 1
    fi
}

show_hermes_status() {
    log_info "Hermes Adapter Status:"
    echo ""
    if [ -f "$HERMES_PRINCIPAL_FILE" ]; then
        echo "  State: initialized"
        echo "  Authority: observe-only + summary append"
        echo "  File: $HERMES_PRINCIPAL_FILE"
        cat "$HERMES_PRINCIPAL_FILE" | python3 -m json.tool 2>/dev/null | sed 's/^/    /' || cat "$HERMES_PRINCIPAL_FILE"
    else
        echo "  State: not initialized"
    fi
    echo ""
    echo "  Daemon: $(is_daemon_running && echo 'running' || echo 'stopped')"
}

# Parse arguments
case "${1:-}" in
    --stop)
        log_info "Stopping Hermes adapter daemon"
        if [ -f "$PID_FILE" ]; then
            PID=$(cat "$PID_FILE")
            if kill -0 "$PID" 2>/dev/null; then
                kill "$PID" 2>/dev/null || true
                sleep 1
                kill -9 "$PID" 2>/dev/null || true
            fi
            rm -f "$PID_FILE"
        fi
        log_info "Hermes adapter stopped"
        exit 0
        ;;
    --status)
        show_hermes_status
        exit 0
        ;;
    "")
        # Default: bootstrap
        start_daemon_if_needed
        create_hermes_state
        verify_hermes_connection
        echo ""
        log_info "Hermes adapter bootstrap complete"
        echo ""
        echo "hermes_principal_id=hermes-adapter-001"
        echo "authority_scope=observe"
        echo "summary_append_enabled=true"
        echo "milestone=1"
        ;;
    *)
        echo "Usage: $0 [--stop|--status]"
        exit 1
        ;;
esac