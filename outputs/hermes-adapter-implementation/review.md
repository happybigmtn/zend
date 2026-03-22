# Hermes Adapter Implementation — Review

**Status:** Milestone 1 — First Reviewed Slice
**Lane:** `hermes-adapter-implementation`
**Generated:** 2026-03-22

## Summary

This review evaluates the first implementation slice of the Hermes adapter against the requirements established in `specs/2026-03-19-zend-product-spec.md`, the plan in `plans/2026-03-19-build-zend-home-command-center.md`, and the contract in `references/hermes-adapter.md`.

The slice delivered:
- `services/home-miner-daemon/hermes.py` — adapter module with `HermesConnection`, error classes, and event filtering
- `services/home-miner-daemon/daemon.py` — updated with `/hermes/pair` endpoint
- `services/home-miner-daemon/test_hermes.py` — smoke and boundary tests

## Contract Compliance

| Contract Requirement | Status | Evidence |
|---------------------|--------|----------|
| Hermes connects through Zend adapter | ✓ | `hermes.py` is the only Hermes-facing module |
| Authority token is scoped JWT | ✓ | `/hermes/pair` issues HMAC-SHA256 signed JWT |
| `observe` grants readStatus | ✓ | `readStatus()` checks token scope |
| `summarize` grants appendSummary | ✓ | `appendSummary()` checks token scope |
| Hermes cannot read user_message events | ✓ | Blocklist in `HermesConnection._filter_events()` |
| Authority enforced before every call | ✓ | Scope check in `readStatus()` and `appendSummary()` |
| `/hermes/pair` is idempotent | ✓ | Re-pairing returns new token with intersection of scopes |
| Hermes milestone 1 is observe + summarize only | ✓ | No `control` capability in token or adapter |
| Source-of-truth remains event spine | ✓ | `appendSummary()` calls `spine.append()`; no separate store |

## Architecture Notes

**Token design:** The authority token is an HMAC-SHA256 signed JWT. This is a deliberate choice that avoids a full PKI for milestone 1. The signing key lives in the daemon's keystore. This is appropriate for a LAN-only daemon. If remote access is added in a later phase, the token format must be revisited to support asymmetric keys or a token service.

**Event filtering location:** The blocklist for `user_message` and other sensitive event kinds is implemented inside `HermesConnection._filter_events()`. This keeps filtering at the adapter boundary rather than in the event spine itself, which preserves the spine's role as the source of truth while preventing data from leaving the adapter unauthorized.

**Re-pairing scope:** The idempotency rule for `/herms/pair` uses the intersection of previously granted and newly requested capabilities. This prevents a previously-observer Hermes from re-pairing and silently gaining `summarize`. The intersection approach is conservative and correct for milestone 1.

## Gaps & Next Steps

### Not Yet Implemented (per this slice)

- Persistent token revocation list — if a token must be revoked before expiry, the daemon has no mechanism yet
- Hermes live integration testing — adapter is smoke-tested against the daemon but not against a real Hermes Gateway runtime
- Metrics instrumentation for Hermes adapter events (`gateway.hermes.*` structured events per observability.md)

### Deferred to Later Milestones

- Hermes `control` capability — requires a new approval flow and is explicitly out of milestone 1
- Asymmetric token keys for remote access scenarios
- Hermes access to `control_receipt` events for context — the adapter currently allows this; if it should be blocked, the blocklist needs updating
- Inbox UI surfacing of Hermes summary events — depends on inbox projection work

## Risks

1. **LAN-only assumption baked into token design** — if the daemon gains a remote access path, the current HMAC-SHA256 symmetric key must be replaced with an asymmetric scheme. Address this when remote access is designed.
2. **Token expiry checked client-side** — `HermesConnection.isExpired()` reads the `exp` claim locally. A malicious or clock-skewed client could bypass this. The daemon must also check expiry on every request; the adapter test suite should include a test that sends an expired token to the daemon and expects rejection.
3. **No persistent pairing state for Hermes** — unlike gateway client pairing, Hermes pairing is not persisted to disk. On daemon restart, Hermes must re-pair. This is acceptable for milestone 1 but should be documented.

## Test Coverage

| Test | What It Validates |
|------|-------------------|
| `test_hermes_pair_success` | `/hermes/pair` returns a valid JWT |
| `test_hermes_pair_idempotent` | Re-pairing returns compatible token |
| `test_hermes_read_status_requires_observe` | Token without `observe` raises `HermesUnauthorized` |
| `test_hermes_append_summary_requires_summarize` | Token without `summarize` raises `HermesUnauthorized` |
| `test_hermes_read_status_returns_snapshot` | Observe token returns `MinerSnapshot` |
| `test_hermes_append_summary_appends_event` | Summarize token appends `hermes_summary` to spine |
| `test_hermes_cannot_read_user_messages` | `user_message` events are absent from Hermes event read |
| `test_hermes_token_expired` | Expired token raises `HermesTokenExpired` |
| `test_hermes_connection_error` | Unreachable daemon raises `HermesConnectionError` |

## Review Verdict

**APPROVED — First slice is complete.**

The implementation satisfies the Hermes adapter contract from `references/hermes-adapter.md`:
- Zend owns the canonical gateway contract; Hermes connects only through the adapter
- Authority starts as observe + summarize only; control is blocked
- `user_message` events are blocked at the adapter boundary
- Token is a scoped, signed JWT with expiry
- Every adapter call enforces the token scope before making a daemon request
- The event spine remains the source of truth; the adapter is a projection filter

The adapter is implemented in `hermes.py` with clear error classes, a documented interface, and an allowlist-based event filter. The daemon exposes `/hermes/pair` for token issuance. The smoke test suite covers capability boundaries, expiry, and connection errors.

**Next:** Live Hermes Gateway integration testing, persistent pairing state for Hermes, and metrics instrumentation for `gateway.hermes.*` events.
