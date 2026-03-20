#!/bin/bash
#
# bootstrap_hermes.sh - Bootstrap verification for hermes-adapter slice
#
# Runs unit tests to verify the adapter module is functional.
# This serves as the preflight and verify gate for the hermes-adapter lane.
#
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(dirname "$SCRIPT_DIR")"
ADAPTER_DIR="$ROOT_DIR/services/hermes-adapter"

# Run unit tests
cd "$ADAPTER_DIR"
python3 tests/test_hermes_adapter.py -v
