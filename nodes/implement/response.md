## Summary

Implemented the `hermes-adapter:hermes-adapter` slice:

### Files Created

```
scripts/bootstrap_hermes.sh              [new - proof-of-life]
services/hermes-adapter/__init__.py      [new - public exports]
services/hermes-adapter/adapter.py        [new - HermesAdapter class]
outputs/hermes-adapter/implementation.md  [new - implementation doc]
outputs/hermes-adapter/verification.md    [new - verification doc]
```

### Proof Gate

`./scripts/bootstrap_hermes.sh` **PASSED** — all capabilities verified:

- Daemon health check ✓
- Adapter connects with `observe` + `summarize` scope ✓
- `readStatus()` returns miner snapshot ✓
- `appendSummary()` writes to event spine ✓
- `getScope()` reflects granted capabilities ✓

### Key Implementation Notes

1. **Capability enforcement** — `_require_capability()` checks scope before any relay, enforcing milestone 1 boundaries (no direct miner control)

2. **Event spine integration** — Summaries are appended as `hermes_summary` events, keeping Hermes output on the append-only journal per architecture

3. **Token format** — Authority tokens are `device_name:capability1,capability2` (e.g., `hermes-gateway:observe,summarize`) — milestone 1 uses simple format; real tokens would be base64-encoded JSON