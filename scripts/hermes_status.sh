#!/bin/bash
#
# hermes_status.sh - Report Hermes adapter health and authority state
#
# Usage:
#   ./scripts/hermes_status.sh
#
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(dirname "$SCRIPT_DIR")"
STATE_DIR="${ZEND_STATE_DIR:-$ROOT_DIR/state}"

HERMES_PRINCIPAL_FILE="$STATE_DIR/hermes/principal.json"
SPINE_FILE="$STATE_DIR/event-spine.jsonl"
PID_FILE="$STATE_DIR/daemon.pid"

BIND_HOST="${ZEND_BIND_HOST:-127.0.0.1}"
BIND_PORT="${ZEND_BIND_PORT:-8080}"

GREEN='\033[0;32m'
NC='\033[0m'

log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

run_status_probe() {
    python3 - "$HERMES_PRINCIPAL_FILE" "$SPINE_FILE" "$PID_FILE" "$BIND_HOST" "$BIND_PORT" <<'PY'
import json
import os
import socket
import sys
from pathlib import Path

principal_path = Path(sys.argv[1])
spine_path = Path(sys.argv[2])
pid_path = Path(sys.argv[3])
host = sys.argv[4]
port = int(sys.argv[5])


def load_principal() -> tuple[str, dict]:
    if not principal_path.exists():
        return "missing", {}
    with principal_path.open() as handle:
        return "initialized", json.load(handle)


def daemon_pid_status() -> tuple[str, str]:
    if not pid_path.exists():
        return "missing", ""

    raw_pid = pid_path.read_text().strip()
    if not raw_pid:
        return "stale", ""

    try:
        pid = int(raw_pid)
    except ValueError:
        return "stale", raw_pid

    proc_path = Path(f"/proc/{pid}")
    if not proc_path.exists():
        return "stale", str(pid)

    try:
        cmdline = (proc_path / "cmdline").read_text()
    except OSError:
        cmdline = ""

    if cmdline and "daemon.py" not in cmdline:
        return "stale", str(pid)

    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return "stale", str(pid)
    except PermissionError:
        if cmdline:
            return "running", str(pid)
        return "stale", str(pid)

    return "running", str(pid)


def daemon_endpoint_status() -> str:
    try:
        with socket.create_connection((host, port), timeout=0.5):
            return "reachable"
    except PermissionError:
        return "probe_blocked"
    except OSError as exc:
        if exc.errno == 1:
            return "probe_blocked"
        return "unreachable"


def hermes_summary_snapshot(principal_id: str) -> tuple[int, str]:
    count = 0
    latest_created_at = ""

    if not principal_id or not spine_path.exists():
        return count, latest_created_at

    with spine_path.open() as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue

            event = json.loads(line)
            if event.get("kind") != "hermes_summary":
                continue
            if principal_id and event.get("principal_id") != principal_id:
                continue

            count += 1
            latest_created_at = event.get("created_at", latest_created_at)

    return count, latest_created_at


principal_state, principal = load_principal()
principal_id = principal.get("principal_id", "")
authority_scope = principal.get("authority_scope", [])
capabilities = principal.get("capabilities", [])
summary_append_enabled = principal.get("summary_append_enabled", False)
milestone = principal.get("milestone", "")

daemon_state, daemon_pid = daemon_pid_status()
endpoint_state = daemon_endpoint_status() if daemon_state == "running" else "skipped"
summary_count, last_summary_at = hermes_summary_snapshot(principal_id)

issues = []
if principal_state != "initialized":
    issues.append("principal_missing")
else:
    if authority_scope != ["observe"]:
        issues.append("authority_scope_unexpected")
    if capabilities != ["observe"]:
        issues.append("capabilities_unexpected")
    if summary_append_enabled is not True:
        issues.append("summary_append_disabled")
    if milestone != 1:
        issues.append("milestone_unexpected")

if daemon_state != "running":
    issues.append("daemon_not_running")
elif endpoint_state != "reachable":
    issues.append(
        "daemon_endpoint_unverified"
        if endpoint_state == "probe_blocked"
        else "daemon_endpoint_unreachable"
    )

if summary_count == 0:
    issues.append("hermes_summary_missing")

overall_status = "healthy" if not issues else "degraded"

print(f"  principal_state={principal_state}")
print(f"  principal_id={principal_id or 'missing'}")
print(f"  capabilities={','.join(capabilities) if capabilities else 'missing'}")
print(f"  authority_scope={','.join(authority_scope) if authority_scope else 'missing'}")
print(f"  summary_append_enabled={str(summary_append_enabled).lower()}")
print(f"  milestone={milestone if milestone != '' else 'missing'}")
print(f"  daemon_pid_status={daemon_state}")
print(f"  daemon_pid={daemon_pid or 'missing'}")
print(f"  daemon_endpoint={endpoint_state}")
print(f"  hermes_summary_count={summary_count}")
print(f"  last_hermes_summary_at={last_summary_at or 'missing'}")
print(f"  overall_status={overall_status}")
print(f"  issues={','.join(issues) if issues else 'none'}")

sys.exit(0 if not issues else 1)
PY
}

log_info "Hermes Adapter Status:"
echo ""

if STATUS_OUTPUT="$(run_status_probe)"; then
    STATUS_CODE=0
else
    STATUS_CODE=$?
fi

printf '%s\n' "$STATUS_OUTPUT"
exit "$STATUS_CODE"
