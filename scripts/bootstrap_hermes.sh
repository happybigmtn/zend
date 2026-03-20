#!/bin/bash
#
# bootstrap_hermes.sh - Bootstrap the Hermes Adapter slice
#
# This script:
# 1. Verifies outputs/hermes-adapter/ directory exists with required artifacts
# 2. Validates agent-adapter.md contract
# 3. Proves the hermes-adapter slice is bootstrapped
#
# Usage:
#   ./scripts/bootstrap_hermes.sh
#
set +e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(dirname "$SCRIPT_DIR")"
OUTPUT_DIR="$ROOT_DIR/outputs/hermes-adapter"

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

# Check outputs directory exists
if [ ! -d "$OUTPUT_DIR" ]; then
    log_error "Hermes adapter outputs not found: $OUTPUT_DIR"
    exit 1
fi

# Check required artifacts
REQUIRED_ARTIFACTS=(
    "agent-adapter.md"
    "review.md"
)

for artifact in "${REQUIRED_ARTIFACTS[@]}"; do
    if [ ! -f "$OUTPUT_DIR/$artifact" ]; then
        log_error "Missing required artifact: $OUTPUT_DIR/$artifact"
        exit 1
    fi
done

# Validate agent-adapter.md content
AGENT_ADAPTER_FILE="$OUTPUT_DIR/agent-adapter.md"

# Check for HermesAdapter interface
if ! grep -q "HermesAdapter" "$AGENT_ADAPTER_FILE"; then
    log_error "agent-adapter.md missing HermesAdapter interface"
    exit 1
fi

# Check for required methods
REQUIRED_METHODS=(
    "connect"
    "readStatus"
    "appendSummary"
    "getScope"
)

for method in "${REQUIRED_METHODS[@]}"; do
    if ! grep -q "$method" "$AGENT_ADAPTER_FILE"; then
        log_error "agent-adapter.md missing required method: $method"
        exit 1
    fi
done

# Check for HermesCapability type
if ! grep -q "HermesCapability" "$AGENT_ADAPTER_FILE"; then
    log_error "agent-adapter.md missing HermesCapability type"
    exit 1
fi

# Check for authority scope enforcement
if ! grep -q "observe" "$AGENT_ADAPTER_FILE" || ! grep -q "summarize" "$AGENT_ADAPTER_FILE"; then
    log_error "agent-adapter.md missing capability scopes (observe/summarize)"
    exit 1
fi

# Validate review.md content
REVIEW_FILE="$OUTPUT_DIR/review.md"

if ! grep -q "hermes-adapter" "$REVIEW_FILE"; then
    log_error "review.md does not reference hermes-adapter"
    exit 1
fi

log_info "Hermes Adapter slice bootstrapped successfully"
log_info "  - agent-adapter.md: valid contract"
log_info "  - review.md: valid review artifact"
exit 0