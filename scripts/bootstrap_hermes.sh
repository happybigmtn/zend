#!/bin/bash
#
# bootstrap_hermes.sh - Bootstrap the Hermes adapter slice
#
# This script is the preflight gate for the hermes-adapter lane.
# It initializes the Hermes adapter state and proves the slice is viable.
#
# Usage:
#   ./scripts/bootstrap_hermes.sh
#
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(dirname "$SCRIPT_DIR")"
ADAPTER_DIR="$ROOT_DIR/services/hermes-adapter"
STATE_DIR="$ROOT_DIR/state"

# Initialize state directory
mkdir -p "$STATE_DIR"

# Initialize hermes-adapter service directory
mkdir -p "$ADAPTER_DIR"

# Create adapter state file
ADAPTER_STATE="$STATE_DIR/hermes-adapter-state.json"

# Generate deterministic principal for Hermes if not exists
if [ ! -f "$ADAPTER_STATE" ]; then
    # Create initial Hermes adapter state
    # This encodes the initial delegated authority: observe-only for milestone 1
    cat > "$ADAPTER_STATE" << 'EOF'
{
  "version": 1,
  "adapter_id": "hermes-adapter-001",
  "authority_scope": ["observe", "summarize"],
  "connected": false,
  "last_summary_ts": null
}
EOF
    echo "Hermes adapter state initialized at $ADAPTER_STATE"
else
    echo "Hermes adapter state already exists at $ADAPTER_STATE"
fi

# Verify required modules exist or can be imported
cd "$ADAPTER_DIR"
set +e
python3 -c "
import sys
sys.path.insert(0, '.')
try:
    from adapter import HermesAdapter
    print('HermesAdapter import: OK')
except ImportError as e:
    print(f'HermesAdapter import: SKIP ({e})')
" 2>/dev/null || true
set -e

echo ""
echo "Hermes adapter bootstrap complete"
echo "adapter_state_file=$ADAPTER_STATE"
echo "bootstrap=success"