`★ Insight ─────────────────────────────────────`
**Fixup idempotency pattern**: Both `bootstrap_home_miner.sh` and `pair_gateway_client.sh` needed to handle the "already paired" case. The pairing script was treating the CLI's error JSON as a script failure due to `set -e`, when in fact the device existing is a valid/idempotent state for a verify script that runs multiple times.
`─────────────────────────────────────────────────`

## Summary

**Fixed:** `scripts/pair_gateway_client.sh` - Added idempotent handling for "already paired" devices.

**Root cause:** The verify script re-runs pairing commands even when devices were paired in a previous run. `bootstrap_home_miner.sh` already handled this case, but `pair_gateway_client.sh` exited with the CLI's error code instead of treating "already paired" as success.

**Change made to `pair_gateway_client.sh`:**
```bash
# After CLI call returns non-zero, check for idempotent "already paired"
if echo "$OUTPUT" | grep -q "already paired"; then
    echo ""
    echo "paired $CLIENT"
    echo "capability=$(echo "$CAPABILITIES" | tr ',' ' ')"
    exit 0
fi
```

**Verification:**
- First proof gate (`./scripts/bootstrap_home_miner.sh`): **PASS**
- Full verify sequence: **PASS** (requires `unset ZEND_BIND_PORT` to use default 8080)