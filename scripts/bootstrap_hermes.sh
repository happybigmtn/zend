#!/bin/bash
#
# bootstrap_hermes.sh - Bootstrap the Hermes adapter
#
# This script:
# 1. Ensures the home-miner daemon is running
# 2. Creates a Hermes principal with observe + summarize capabilities
# 3. Emits a pairing event for Hermes on the event spine
#
# Usage:
#   ./scripts/bootstrap_hermes.sh
#
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(dirname "$SCRIPT_DIR")"
DAEMON_DIR="$ROOT_DIR/services/home-miner-daemon"
STATE_DIR="$ROOT_DIR/state"

# Default daemon binding
BIND_HOST="${ZEND_BIND_HOST:-127.0.0.1}"
BIND_PORT="${ZEND_BIND_PORT:-8080}"

PID_FILE="$STATE_DIR/daemon.pid"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

log_info() { echo -e "${GREEN}[INFO]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

ensure_daemon() {
    if [ -f "$PID_FILE" ]; then
        PID=$(cat "$PID_FILE" 2>/dev/null)
        if [ -n "$PID" ] && kill -0 "$PID" 2>/dev/null; then
            log_info "Daemon already running (PID: $PID)"
            return 0
        fi
        rm -f "$PID_FILE"
    fi

    log_info "Daemon not running — starting it..."
    mkdir -p "$STATE_DIR"
    export ZEND_STATE_DIR="$STATE_DIR"
    export ZEND_BIND_HOST="$BIND_HOST"
    export ZEND_BIND_PORT="$BIND_PORT"

    cd "$DAEMON_DIR"
    python3 daemon.py &
    DAEMON_PID=$!
    echo "$DAEMON_PID" > "$PID_FILE"

    log_info "Waiting for daemon on $BIND_HOST:$BIND_PORT..."
    for i in {1..10}; do
        if curl -s "http://$BIND_HOST:$BIND_PORT/health" > /dev/null 2>&1; then
            log_info "Daemon ready"
            return 0
        fi
        sleep 0.5
    done

    log_error "Daemon failed to start"
    return 1
}

bootstrap_hermes() {
    log_info "Bootstrapping Hermes principal with observe + summarize..."

    cd "$DAEMON_DIR"
    python3 -c "
import sys
sys.path.insert(0, '.')
from store import load_or_create_principal, pair_client, get_pairing_by_device
from spine import append_pairing_granted, append_hermes_summary
from datetime import datetime, timezone
import json

principal = load_or_create_principal()

# Check if Hermes is already paired (idempotent)
existing = get_pairing_by_device('hermes-gateway')
if existing:
    pairing = existing
    print(json.dumps({
        'principal_id': principal.id,
        'device_name': pairing.device_name,
        'capabilities': pairing.capabilities,
        'paired_at': pairing.paired_at,
        'note': 'already paired (idempotent)'
    }, indent=2))
else:
    # Create Hermes device pairing with observe + summarize
    pairing = pair_client('hermes-gateway', ['observe', 'summarize'])

    # Emit Hermes summary to establish event-spine presence
    append_hermes_summary(
        'Hermes adapter bootstrapped: observe + summarize granted',
        ['observe', 'summarize'],
        principal.id
    )

    # Emit pairing granted event
    append_pairing_granted('hermes-gateway', ['observe', 'summarize'], principal.id)

    print(json.dumps({
        'principal_id': principal.id,
        'device_name': pairing.device_name,
        'capabilities': pairing.capabilities,
        'paired_at': pairing.paired_at
    }, indent=2))
"
}

main() {
    ensure_daemon || exit 1
    bootstrap_hermes
    log_info "Hermes adapter bootstrapped successfully"
    return 0
}

main "$@"