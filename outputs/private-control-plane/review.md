# Private Control Plane — Review

**Status:** Milestone 1 Implementation Review
**Generated:** 2026-03-20
**Reviewer:** Automated Lane Review

## Summary

This review evaluates the private control plane implementation slice for Zend against the contract defined in `control-plane-contract.md`.

## Contract Compliance

### Principal Identity ✓

| Requirement | Status | Evidence |
|-------------|--------|----------|
| PrincipalId is UUID v4 | ✓ | `store.py:61` creates `uuid.uuid4()` |
| Shared across pairing and events | ✓ | `cli.py:95,142` loads principal for all operations |
| Stable identity | ✓ | Principal persisted in `state/principal.json` |

### Capability-Scoped Pairing ✓

| Requirement | Status | Evidence |
|-------------|--------|----------|
| `observe` capability allows status read | ✓ | `cli.py:47-54` checks observe or control |
| `control` capability allows start/stop/mode | ✓ | `cli.py:134` checks `has_capability(..., 'control')` |
| Observe-only cannot issue control | ✓ | `cli.py:134-139` returns unauthorized |
| Duplicate device names rejected | ✓ | `store.py:99-101` raises ValueError |

### Event Spine ✓

| Requirement | Status | Evidence |
|-------------|--------|----------|
| Append-only journal | ✓ | `spine.py:64` appends to `.jsonl` |
| All events flow through spine | ✓ | `cli.py:89-93,106-115,156-162` append before responding |
| Inbox is derived view | ✓ | `cli.py:191` queries spine for inbox events |
| Event kinds implemented | ✓ | `spine.py:29-36` all 7 EventKind values |

### Source of Truth Constraint ✓

**CRITICAL constraint verified:** `spine.py` is the only event store. No feature writes directly to a separate receipt/alert store.

## Preflight Verification

The preflight script executed successfully:

```
bootstrap_home_miner.sh     → Daemon started on 127.0.0.1:8080
pair_gateway_client.sh       → alice-phone paired (observe)
curl /miner/stop            → GATEWAY_UNAUTHORIZED (correct!)
pair_gateway_client.sh       → bob-phone paired (observe,control)
set_mining_mode.sh          → accepted by home miner
curl /spine/events          → Events returned
```

### Key Behaviors Verified

1. **Capability enforcement:** Direct HTTP call to `/miner/stop` without capability record returned `GATEWAY_UNAUTHORIZED`
2. **Control acceptance:** bob-phone with `control` capability successfully changed mode
3. **Event append:** Control receipt appended to spine after mode change
4. **Principal persistence:** alice-phone already paired on re-run (state preserved)

## Gaps

### Deferred Per Contract

| Item | Reason |
|------|--------|
| Real Hermes adapter connection | Observe-only + summary append is milestone 1 scope |
| Rich inbox UX | Operations inbox only for milestone 1 |
| Event encryption | Plaintext JSON in milestone 1; encryption deferred |

### Not Yet Tested

| Item | Status |
|------|--------|
| Token expiration | Token created but not enforced in daemon |
| Capability revocation | Revocation flow not exposed via CLI |
| Conflict detection | Two simultaneous control commands |

## Risks

1. **Plaintext event payloads** — `spine.py` writes JSON to `.jsonl` without encryption. Acceptable for milestone 1 simulator but must be addressed before production.
2. **No token expiration enforcement** — `token_expires_at` is stored but not checked on requests.
3. **No conflict resolution** — Concurrent control commands could race. The lock in `MinerSimulator` serializes locally but there's no distributed conflict detection.

## Review Verdict

**APPROVED — Contract slice is implemented correctly.**

The implementation satisfies the control-plane contract:
- PrincipalId shared across pairing and events
- Capability-scoped pairing with observe/control
- Event spine as source of truth
- CLI enforcement of capability boundaries

Next: Integration testing, Hermes adapter implementation, event encryption.
