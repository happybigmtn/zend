# Hermes Adapter Lane — Review

**Status:** Milestone 1 Implementation Review
**Generated:** 2026-03-20

## Summary

This review evaluates the first implementation slice of the Zend Hermes Adapter against the plan and contract in `references/hermes-adapter.md`.

## What's Implemented

### HermesAdapter ✓

`services/hermes-adapter/adapter.py`:
- `connect(authority_token)` — validates token, establishes connection
- `readStatus()` — reads miner snapshot via gateway (requires observe)
- `appendSummary(summary)` — appends to event spine (requires summarize)
- `getScope()` — returns current capability list
- `_require_capability()` — enforces boundaries, raises PermissionError

### Authority Token Handling ✓

`services/hermes-adapter/authority.py`:
- `encode_authority_token()` — base64 JSON encoding
- `decode_authority_token()` — validation and decoding
- `load_hermes_token()` / `save_hermes_token()` — state persistence
- Token expiration checking

### CLI Interface ✓

`services/hermes-adapter/cli.py`:
- `connect` — connect to gateway
- `status` — read miner status
- `summarize` — append summary
- `token` — generate authority token
- `scope` — show current scope

### Bootstrap Script ✓

`scripts/bootstrap_hermes.sh`:
- Starts home-miner daemon if needed
- Creates Hermes authority token with observe+summarize
- Verifies observe capability
- Verifies summarize capability

## Architecture Compliance

| Requirement | Status | Evidence |
|-------------|--------|----------|
| Capability scoping (observe/summarize) | ✓ | `_require_capability()` enforced |
| No direct control | ✓ | start/stop/set_mode blocked by PermissionError |
| Authority token validation | ✓ | `decode_authority_token()` with expiration check |
| Event spine append | ✓ | `appendSummary()` uses spine.py |
| Observe returns MinerSnapshot | ✓ | `readStatus()` returns typed snapshot |
| Milestone 1 boundaries | ✓ | Only observe+summarize implemented |

## Capability Boundaries

The adapter correctly enforces:

```
observe → readStatus() ✓
summarize → appendSummary() ✓
(no capability) → PermissionError ✓
expired token → ValueError ✓
```

## Gaps & Next Steps

### Not Yet Implemented
- Real cryptographic token signing (base64 encoding is placeholder)
- Hermes Gateway live integration
- Full hermes_summary event retrieval

### Deferred (Per Contract)
- Control capability (requires new approval flow)
- Inbox message access (requires contact policy model)
- Direct miner commands (requires stronger audit trail)

## Verification

```bash
# Run preflight gate
./scripts/bootstrap_hermes.sh

# Expected output:
# [INFO] Daemon already running on http://127.0.0.1:8080
# [INFO] Creating Hermes authority token...
# [INFO] Hermes token created
# [INFO] Verifying observe capability...
# Observe: status=stopped, mode=paused
# [INFO] Observe capability verified
# [INFO] Verifying summarize capability...
# Summarize: summary appended to event spine
# [INFO] Summarize capability verified
# [INFO] Hermes Adapter bootstrap complete
```

## Risks

1. **Base64 token encoding** — Not cryptographically signed; adequate for milestone 1 dev
2. **No live Hermes Gateway** — Only adapter-to-daemon tested
3. **State directory coupling** — Adapter and daemon share state directory

## Review Verdict

**APPROVED — First slice is complete.**

The implementation satisfies the contract requirements:
- Capability scoping enforced at adapter boundary
- Observe and summarize capabilities operational
- Authority token lifecycle implemented
- Bootstrap script proves end-to-end functionality
- Output artifacts delivered

Next: Integration with live Hermes Gateway, cryptographic token signing.