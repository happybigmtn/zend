#!/bin/bash
#
# bootstrap_hermes.sh - Bootstrap the Hermes Adapter
#
# This script:
# 1. Initializes hermes-adapter state directory
# 2. Creates a demo authority token for milestone 1
# 3. Connects the adapter to the Zend gateway
# 4. Verifies observe and summarize capabilities
#
# Usage:
#   ./scripts/bootstrap_hermes.sh
#   ./scripts/bootstrap_hermes.sh --verify
#
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(dirname "$SCRIPT_DIR")"
ADAPTER_DIR="$ROOT_DIR/services/hermes-adapter"
STATE_DIR="$ROOT_DIR/state/hermes-bootstrap"
PRINCIPAL_ID="hermes-demo-principal"

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

# Reset proof state for deterministic runs
rm -rf "$STATE_DIR"
mkdir -p "$STATE_DIR"

# Set environment
export ZEND_STATE_DIR="$STATE_DIR"
export ROOT_DIR
export HERMES_PRINCIPAL_ID="$PRINCIPAL_ID"

make_token() {
    python3 - "$1" "$2" <<'PY'
import base64
import json
import sys

principal_id = sys.argv[1]
capabilities = [cap for cap in sys.argv[2].split(",") if cap]
token = {
    "principal_id": principal_id,
    "capabilities": capabilities,
    "expires_at": None,
}
print(base64.b64encode(json.dumps(token).encode()).decode())
PY
}

seed_control_receipts() {
    python3 - <<'PY'
import os
import sys
from pathlib import Path

root_dir = Path(os.environ["ROOT_DIR"])
sys.path.insert(0, str(root_dir / "services" / "home-miner-daemon"))

import spine

principal_id = os.environ["HERMES_PRINCIPAL_ID"]
spine.append_control_receipt("start", None, "accepted", principal_id)
spine.append_control_receipt("set_mode", "balanced", "accepted", principal_id)
PY
}

assert_last_summary_event() {
    python3 - "$STATE_DIR" "$1" "$PRINCIPAL_ID" <<'PY'
import json
import os
import sys

state_dir, event_id, principal_id = sys.argv[1:4]
spine_path = os.path.join(state_dir, "event-spine.jsonl")

with open(spine_path, "r", encoding="utf-8") as handle:
    events = [json.loads(line) for line in handle if line.strip()]

if not events:
    raise SystemExit("no events found")

event = events[-1]
if event.get("id") != event_id:
    raise SystemExit("summary event id mismatch")
if event.get("kind") != "hermes_summary":
    raise SystemExit("last event is not hermes_summary")
if event.get("principal_id") != principal_id:
    raise SystemExit("summary principal mismatch")
if event.get("payload", {}).get("summary_text") != "Hermes adapter bootstrap test summary":
    raise SystemExit("summary payload mismatch")
PY
}

bootstrap_adapter() {
    log_info "Bootstrapping Hermes Adapter..."

    # Verify adapter module exists
    if [ ! -d "$ADAPTER_DIR" ]; then
        log_error "Hermes adapter directory not found: $ADAPTER_DIR"
        exit 1
    fi

    # Run connection via CLI
    cd "$ADAPTER_DIR"
    FULL_TOKEN="$(make_token "$PRINCIPAL_ID" "observe,summarize")"
    OUTPUT=$(python3 cli.py connect --token "$FULL_TOKEN" 2>&1)

    if [ $? -eq 0 ]; then
        CONNECTION_ID=$(echo "$OUTPUT" | python3 -c "import sys,json; print(json.load(sys.stdin).get('connection_id', ''))" 2>/dev/null || echo "")
        PRINCIPAL_ID=$(echo "$OUTPUT" | python3 -c "import sys,json; print(json.load(sys.stdin).get('principal_id', ''))" 2>/dev/null || echo "")

        if [ -n "$CONNECTION_ID" ]; then
            log_info "Adapter connected successfully"
            log_info "Connection ID: $CONNECTION_ID"
            log_info "Principal ID: $PRINCIPAL_ID"
            return 0
        fi
    fi

    log_error "Adapter connection failed: $OUTPUT"
    exit 1
}

verify_capabilities() {
    log_info "Verifying Hermes capabilities..."

    cd "$ADAPTER_DIR"
    seed_control_receipts

    # Check scope
    SCOPE_OUTPUT=$(python3 cli.py scope 2>&1)
    SCOPE=$(echo "$SCOPE_OUTPUT" | python3 -c "import sys,json; print(','.join(json.load(sys.stdin).get('scope', [])))" 2>/dev/null || echo "")

    if echo "$SCOPE" | grep -q "observe"; then
        log_info "  [OK] observe capability"
    else
        log_error "  [FAIL] observe capability missing"
        exit 1
    fi

    if echo "$SCOPE" | grep -q "summarize"; then
        log_info "  [OK] summarize capability"
    else
        log_error "  [FAIL] summarize capability missing"
        exit 1
    fi

    # Test observe capability against seeded control receipts
    STATUS_OUTPUT=$(python3 cli.py status 2>&1)
    STATUS=$(echo "$STATUS_OUTPUT" | python3 -c "import sys,json; print(json.load(sys.stdin).get('status', ''))" 2>/dev/null || echo "")
    MODE=$(echo "$STATUS_OUTPUT" | python3 -c "import sys,json; print(json.load(sys.stdin).get('mode', ''))" 2>/dev/null || echo "")
    if [ "$STATUS" = "running" ] && [ "$MODE" = "balanced" ]; then
        log_info "  [OK] status read via observe"
    else
        log_error "  [FAIL] observe returned unexpected snapshot: $STATUS_OUTPUT"
        exit 1
    fi

    # Test summarize capability (append summary)
    SUMMARY_OUTPUT=$(python3 cli.py summary --text "Hermes adapter bootstrap test summary" 2>&1)
    if echo "$SUMMARY_OUTPUT" | grep -q "event_id"; then
        EVENT_ID=$(echo "$SUMMARY_OUTPUT" | python3 -c "import sys,json; print(json.load(sys.stdin).get('event_id', ''))" 2>/dev/null || echo "")
        assert_last_summary_event "$EVENT_ID"
        log_info "  [OK] summary appended: $EVENT_ID"
    else
        log_error "  [FAIL] summary append failed: $SUMMARY_OUTPUT"
        exit 1
    fi

    # Prove capability boundaries for the same adapter surface
    OBSERVE_ONLY_TOKEN="$(make_token "$PRINCIPAL_ID" "observe")"
    python3 cli.py connect --token "$OBSERVE_ONLY_TOKEN" >/dev/null
    set +e
    SUMMARY_DENIED_OUTPUT=$(python3 cli.py summary --text "should fail" 2>&1)
    SUMMARY_DENIED_EXIT=$?
    set -e
    if [ $SUMMARY_DENIED_EXIT -ne 0 ] && echo "$SUMMARY_DENIED_OUTPUT" | grep -q "summarize"; then
        log_info "  [OK] summarize denied without summarize capability"
    else
        log_error "  [FAIL] summarize boundary not enforced"
        exit 1
    fi

    SUMMARIZE_ONLY_TOKEN="$(make_token "$PRINCIPAL_ID" "summarize")"
    python3 cli.py connect --token "$SUMMARIZE_ONLY_TOKEN" >/dev/null
    set +e
    STATUS_DENIED_OUTPUT=$(python3 cli.py status 2>&1)
    STATUS_DENIED_EXIT=$?
    set -e
    if [ $STATUS_DENIED_EXIT -ne 0 ] && echo "$STATUS_DENIED_OUTPUT" | grep -q "observe"; then
        log_info "  [OK] observe denied without observe capability"
    else
        log_error "  [FAIL] observe boundary not enforced"
        exit 1
    fi

    set +e
    INVALID_TOKEN_OUTPUT=$(python3 cli.py connect --token "not-a-token" 2>&1)
    INVALID_TOKEN_EXIT=$?
    set -e
    if [ $INVALID_TOKEN_EXIT -ne 0 ] && echo "$INVALID_TOKEN_OUTPUT" | grep -q "authority token"; then
        log_info "  [OK] invalid authority token rejected"
    else
        log_error "  [FAIL] invalid authority token was accepted"
        exit 1
    fi
}

# Parse arguments
case "${1:-}" in
    --verify)
        verify_capabilities
        exit 0
        ;;
    "")
        # Default: bootstrap and verify
        bootstrap_adapter
        verify_capabilities
        ;;
    *)
        echo "Usage: $0 [--verify]"
        exit 1
        ;;
esac

echo ""
log_info "Hermes Adapter bootstrap complete"
log_info "Capabilities verified: observe, summarize"
log_info "Bootstrap proof: PASS"
