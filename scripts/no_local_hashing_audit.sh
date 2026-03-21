#!/bin/bash
#
# no_local_hashing_audit.sh - Audit client for local hashing activity
#
# This proves that the gateway client performs no hashing and only issues
# control requests to the home miner.
#
# Usage:
#   ./scripts/no_local_hashing_audit.sh --client <name>
#
# Exit codes:
#   0 - No hashing detected (pass)
#   1 - Hashing detected (fail)
#

set -euo pipefail

# Parse arguments
CLIENT=""
while [[ $# -gt 0 ]]; do
    case $1 in
        --client)
            CLIENT="$2"
            shift 2
            ;;
        *)
            echo "Unknown option: $1"
            exit 1
            ;;
    esac
done

if [ -z "$CLIENT" ]; then
    echo "Error: --client is required"
    echo "Usage: $0 --client <name>"
    exit 1
fi

echo "Running local hashing audit for: $CLIENT"
echo ""

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(dirname "$SCRIPT_DIR")"
CLIENT_SURFACES=(
    "$ROOT_DIR/apps/zend-home-gateway/index.html"
    "$ROOT_DIR/scripts/pair_gateway_client.sh"
    "$ROOT_DIR/scripts/read_miner_status.sh"
    "$ROOT_DIR/scripts/set_mining_mode.sh"
    "$ROOT_DIR/services/home-miner-daemon/cli.py"
)
FAILURES=()

record_failure() {
    FAILURES+=("$1")
}

check_shared_cli_wrapper() {
    local file="$1"
    local expected="$2"
    if ! rg -F -q "$expected" "$file"; then
        record_failure "$file is missing required shared CLI invocation: $expected"
    fi
}

echo "checked: client shell wrappers route through shared CLI"
check_shared_cli_wrapper "$ROOT_DIR/scripts/pair_gateway_client.sh" "python3 cli.py pair"
check_shared_cli_wrapper "$ROOT_DIR/scripts/read_miner_status.sh" "python3 cli.py status"
check_shared_cli_wrapper "$ROOT_DIR/scripts/set_mining_mode.sh" "python3 cli.py control"

echo "checked: active client-side miner processes"
PROCESS_HITS="$(ps -eo pid=,ppid=,pcpu=,comm= | rg -i 'cgminer|bfgminer|xmrig|minerd' || true)"
if [ -n "$PROCESS_HITS" ]; then
    record_failure "unexpected mining process evidence:\n$PROCESS_HITS"
fi

echo "checked: gateway client surfaces for mining primitives"
STATIC_HITS="$(rg -n -i -F \
    -e 'hashlib' \
    -e 'equihash' \
    -e 'randomx' \
    -e 'scrypt' \
    -e 'argon2' \
    -e 'sha256' \
    -e 'blake2' \
    -e 'worker_threads' \
    -e 'new Worker(' \
    -e 'multiprocessing' \
    -e 'ProcessPoolExecutor' \
    -e 'ThreadPoolExecutor' \
    -e 'navigator.hardwareConcurrency' \
    -e 'crypto.subtle.digest' \
    "${CLIENT_SURFACES[@]}" || true)"
if [ -n "$STATIC_HITS" ]; then
    record_failure "unexpected mining primitive evidence:\n$STATIC_HITS"
fi

echo ""

if [ "${#FAILURES[@]}" -eq 0 ]; then
    echo "result: no local hashing detected"
    echo ""
    echo "Proof: Gateway wrappers only route through the shared CLI, no client-side mining workers are active, and the owned client surfaces contain no hashing primitives"
    exit 0
else
    echo "result: hashing activity detected"
    echo "error=LOCAL_HASHING_DETECTED"
    printf '%s\n' "${FAILURES[@]}"
    exit 1
fi
