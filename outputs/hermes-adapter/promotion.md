# Hermes Adapter — Promotion

**Status:** Ready for Integration
**Generated:** 2026-03-20

## Promotion Gate

✅ Preflight passed: `./scripts/bootstrap_hermes.sh`
✅ Quality gate passed: All checks complete
✅ Implementation artifact created: `outputs/hermes-adapter/implementation.md`
✅ Verification artifact created: `outputs/hermes-adapter/verification.md`

## What Is Being Promoted

**Slice:** hermes-adapter:hermes-adapter, Slice 1

**Components:**
- `services/hermes-adapter/` — Hermes adapter service
- `scripts/bootstrap_hermes.sh` — Bootstrap and preflight script

**Capabilities added:**
- Hermes can connect with delegated authority
- Hermes can observe miner status (read-only)
- Hermes can append summaries to event spine

## Integration Contract

The promoted slice provides:
1. `HermesAdapter.connect(authority_token)` → establishes connection with observe + summarize capabilities
2. `HermesAdapter.read_status()` → returns miner status from event spine
3. `HermesAdapter.append_summary(text)` → appends hermes_summary to event spine
4. `HermesAdapter.get_scope()` → returns current capability list

## Next Steps

The next slice should implement:
1. Real Hermes Gateway connectivity (WebSocket/HTTP to actual Hermes)
2. Authority token validation with signature verification
3. Connection state persistence
4. Expiry enforcement

## Files to Promote

```
services/hermes-adapter/__init__.py
services/hermes-adapter/adapter.py
services/hermes-adapter/cli.py
scripts/bootstrap_hermes.sh
outputs/hermes-adapter/agent-adapter.md
outputs/hermes-adapter/implementation.md
outputs/hermes-adapter/verification.md
outputs/hermes-adapter/quality.md
```