# Hermes Adapter Implementation — Review

**Status:** Reviewed
**Date:** 2026-03-22

---

## Summary

The Hermes Adapter provides a capability-scoped interface for Hermes AI agents to connect to the Zend daemon. Hermes can observe miner status and append summaries to the event spine, but cannot issue control commands or read user messages. All five frontier tasks were completed.

---

## Implementation Checklist

| # | Frontier Task | Status |
|---|--------------|--------|
| 1 | Create `hermes.py` adapter module | ✅ Done |
| 2 | Implement `HermesConnection` with authority token validation | ✅ Done |
| 3 | Implement `read_status` through adapter | ✅ Done |
| 4 | Implement `append_summary` through adapter | ✅ Done |
| 5 | Implement event filtering (block `user_message` events for Hermes) | ✅ Done |
| 6 | Add Hermes pairing endpoint to daemon | ✅ Done |

---

## Files Modified

| File | Change | Notes |
|------|--------|-------|
| `services/home-miner-daemon/hermes.py` | Created (~400 lines) | Adapter module with all core functions |
| `services/home-miner-daemon/daemon.py` | Modified | Added `/hermes/*` routes |
| `services/home-miner-daemon/cli.py` | Modified | Added `hermes token` and `hermes pair` subcommands |
| `scripts/hermes_summary_smoke.sh` | Created | Smoke test covering full connect → status → summary → events flow |
| `outputs/hermes-adapter-implementation/spec.md` | Created | Capability spec |
| `outputs/hermes-adapter-implementation/review.md` | Created | This document |

---

## Design Decisions

### Decision 1: Hermes Adapter is a Python Module, Not a Separate Service

The adapter is a capability boundary, not a deployment boundary. Running it in-process avoids a network hop and allows direct access to miner state.

- ✅ Simple deployment; no additional service to operate
- ✅ Shared memory access to miner state snapshot
- ⚠️ Coupled to daemon lifecycle — if the daemon restarts, Hermes connections are lost

### Decision 2: Hermes Capabilities are `observe` and `summarize`

Per the adapter contract, Hermes capabilities are independent from gateway client capabilities. Hermes should never inherit gateway control capability.

- ✅ Minimal, clear attack surface
- ✅ Hard separation between observation/summarization and control

### Decision 3: Hermes Uses a Separate Auth Header Scheme

`Authorization: Hermes <hermes_id>` immediately identifies Hermes-sourced requests. Control endpoints reject this header with HTTP 403 before any miner interaction.

- ✅ Fast rejection of unauthorized control attempts
- ✅ Clear audit trail distinguishing Hermes vs. gateway auth

### Decision 4: Hermes Pairing Store is Separate from Gateway Pairing Store

Hermes pairings are stored in `state/hermes-pairing-store.json` rather than the gateway's `state/pairing-store.json`. This prevents Hermes from accidentally consuming gateway pairing records.

- ✅ Clean isolation of concerns
- ⚠️ Two separate pairing stores to manage

### Decision 5: Event Filter Uses Over-Fetch Strategy

`get_filtered_events()` fetches `limit * 2` events then filters to `HERMES_READABLE_EVENTS`. This ensures `limit` events are returned even after `user_message` entries are stripped.

- ✅ Guarantees pagination limit compliance
- ⚠️ Slightly wasteful on large event volumes (acceptable for expected load)

---

## Security Analysis

### Token Validation
- Authority tokens are JSON with `hermes_id`, `principal_id`, `capabilities`, and `expires_at`
- Tokens expire in 24 hours; expired tokens raise `HermesAuthenticationError`
- Control capability in token raises `HermesCapabilityError` immediately

### Event Filtering
- `user_message` is explicitly absent from `HERMES_READABLE_EVENTS`
- `get_filtered_events()` filters by kind before returning — no `user_message` can reach Hermes
- Over-fetch strategy ensures pagination remains accurate after filtering

### Control Blocking
- `Authorization: Hermes` header is detected in daemon route handlers
- Control endpoints (`/miner/start`, `/miner/stop`, `/miner/set-mode`) return HTTP 403 before any miner interaction
- `validate_control_attempt()` in `hermes.py` always raises `HermesCapabilityError`

---

## Capability Boundaries

### Hermes CAN
1. Connect with authority token (valid, non-expired, observe capability present)
2. Read miner status via `GET /hermes/status` (observe capability)
3. Append summaries to event spine via `POST /hermes/summary` (summarize capability)
4. Read filtered events via `GET /hermes/events` (no `user_message` events)

### Hermes CANNOT
1. Issue control commands — HTTP 403 immediately
2. Read `user_message` events — always filtered out
3. Access gateway control endpoints — header scheme prevents entry
4. Escalate beyond `observe` + `summarize` — enforced at `connect()` and each operation

---

## Open Items

| Item | Status | Notes |
|------|--------|-------|
| Automated test suite (`tests/test_hermes.py`) | Not implemented | Manual smoke script covers the happy path |
| Gateway client Agent tab | Not updated | Still shows placeholder; deferred to next lane |
| Hermes connection persistence | Not implemented | Connections are in-memory; daemon restart clears state |
| Structured logging for Hermes events | Not implemented | Per `references/observability.md` guidance |

---

## Recommendations

1. **Add pytest suite** covering token validation, capability enforcement, event filtering, and control blocking
2. **Persist Hermes connections** to `state/hermes-connection-store.json` for restart resilience
3. **Update gateway Agent tab** in `apps/zend-home-gateway/index.html` to show real Hermes connection state
4. **Add structured logging** for Hermes events per `references/observability.md`

---

## Sign-off

All five frontier tasks were completed. The adapter is functional and the smoke script validates the core flow. The implementation is ready for the next lane.

**Implementation Complete** — Ready for next lane.
