`★ Insight ─────────────────────────────────────`
**Root cause**: In bash scripts, you cannot directly emit JSON arrays from scalar variables — `["observe,control"]` is a single string element, not two separate strings. The fix uses `json.dumps()` to serialize the Python list back to a proper JSON array, preserving the `GatewayCapability[]` contract from `inbox-contract.md`.
**Pattern**: When constructing JSON in shell scripts, delegate serialization to Python (or jq) rather than attempting string interpolation. This avoids type errors like array-vs-string that are invisible to casual inspection.
`─────────────────────────────────────────────────`

## Fixup Summary

**Bug fixed**: `scripts/pair_gateway_client.sh` — the idempotent pairing path (line 64) was emitting `["observe,control"]` (single-element array with comma-joined string) instead of `["observe", "control"]` (proper multi-element array).

**Fix**: Changed from `','.join(...)` string concatenation to `json.dumps(...)` for proper JSON serialization of the capabilities list.

**Verification**:
- `./scripts/bootstrap_home_miner.sh` → EXIT 0
- `pair_gateway_client.sh --client bob-phone` → returns `{"capabilities": ["observe", "control"]}` ✓
- `/spine/events` → returns 76 events ✓
- Quality gate → all green (`quality_ready: yes`)

**What was NOT modified** (per Fixup constraints):
- `promotion.md` — owned by Settle stage; `merge_ready: yes` will be set there

The implementation is now contract-compliant. The `promotion.md` state will be refreshed when Settle runs next.