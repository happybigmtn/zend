# Hermes Adapter Implementation — Review

**Status:** Post-fix review
**Generated:** 2026-03-22
**Reviewer:** Nemesis pass (first-principles + coupled-state)

## Summary

The specify stage produced `hermes.py` (adapter module) and Hermes endpoints in `daemon.py`. The adapter's domain model is correct — capabilities, event filtering, pairing lifecycle, and dataclass structure all align with the reference contract at `references/hermes-adapter.md`. Three bugs were found and fixed during review. Several security observations remain as known-acceptable gaps for milestone 1.

## Bugs Fixed During Review

### BUG-1: Duplicate `do_GET` method (daemon.py)

**Severity:** Code defect (dead code)
**Root cause:** The specify stage appended Hermes GET routes by defining a second `do_GET` instead of extending the first. Python silently shadows the first definition.
**Impact:** The first `do_GET` (lines 181-187) was dead code. The second (line 324) handled all routes correctly, so no user-visible failure, but confusing and fragile.
**Fix:** Removed the dead first definition.

### BUG-2: Auth header scheme mismatch (daemon.py)

**Severity:** Blocking — all authenticated Hermes endpoints unusable
**Root cause:** `_get_hermes_auth()` extracted the value after `Hermes ` from the Authorization header and passed it to `hermes_connect()`, which expects a JSON-encoded authority token. The plan documents `Authorization: Hermes hermes-001` (plain string), which fails JSON parsing.
**Impact:** Every Hermes status/summary/events request returns 403 HERMES_UNAUTHORIZED.
**Fix:** Changed `_get_hermes_auth()` to treat the header value as a hermes_id, look up the pairing record, validate expiration, and construct a `HermesConnection` directly. The `connect()` function remains available for programmatic token-based connections.

### BUG-3: `list_devices()` crash after Hermes pairing (store.py)

**Severity:** Crash — affects all callers of `list_devices()`
**Root cause:** Hermes pairings are stored in the shared `pairing-store.json` with fields (`hermes_id`) that don't match `GatewayPairing`'s constructor (`id`). `list_devices()` iterates all entries and tries to construct `GatewayPairing(**data)` for each.
**Impact:** After any Hermes pairing, `list_devices()` raises `TypeError: unexpected keyword argument 'hermes_id'`.
**Fix:** `list_devices()` now skips entries with `hermes:` prefixed keys.

## Pass 1 — First-Principles Challenge

### Trust Boundaries

| Boundary | Assessment |
|----------|------------|
| Hermes cannot control miner | **Partial.** The adapter enforces this for Hermes-specific endpoints. But `/miner/start`, `/miner/stop`, `/miner/set_mode` have no auth at all — Hermes (or anyone) can call them directly. The adapter is a voluntary boundary, not an enforced one. |
| Hermes cannot read user_message | **Enforced.** `HERMES_READABLE_EVENTS` excludes `USER_MESSAGE`. The filter is applied in `get_filtered_events()`. |
| Authority token validates identity | **Weak.** Tokens are unsigned JSON. Anyone who knows a hermes_id can authenticate via the header scheme. For LAN-only milestone 1, this is acceptable. |
| Pairing requires approval | **Not enforced.** `POST /hermes/pair` creates a pairing immediately with no approval flow, no trust sheet, no user confirmation. Any LAN client can register a Hermes agent. |

### Authority Assumptions

1. **Token issuance is open.** `POST /hermes/connect` with just a `hermes_id` returns a full authority token. This is an unauthenticated token dispenser. Acceptable for LAN-only, but must be locked down before any network exposure.

2. **`/hermes/pairings` leaks all pairing data without auth.** Listing pairings requires no authentication. Low risk on LAN, but should be scoped.

3. **Circular import.** `hermes.py:read_status()` does `from daemon import miner` (deferred import). Daemon imports hermes at module level. This works but is fragile — a refactor that moves the import to module level would break both modules.

### Dangerous Actions

| Action | Who Can Trigger | Guard |
|--------|----------------|-------|
| Pair Hermes agent | Any LAN client | None |
| Issue authority token | Any LAN client with hermes_id | Pairing must exist |
| Append summary to spine | Hermes with summarize capability | Capability check |
| Read miner status | Hermes with observe capability | Capability check |
| Start/stop miner | Any LAN client | **None (no auth)** |

## Pass 2 — Coupled-State Review

### Shared Pairing Store

Gateway and Hermes pairings share `pairing-store.json`. The namespace convention (`hermes:` prefix vs UUID keys) prevents key collisions. After BUG-3 fix, `list_devices()` correctly filters Hermes entries. `list_hermes_pairings()` correctly filters gateway entries.

**Remaining concern:** No schema migration mechanism. If pairing format changes, existing entries become invalid. Low risk for milestone 1.

### Event Spine Consistency

`pair_hermes()` emits both `PAIRING_REQUESTED` and `PAIRING_GRANTED` events atomically (no approval step between them). This is honest for milestone 1 but will need refactoring when real approval flows exist — the requested/granted events should bracket an actual approval decision.

`append_summary()` wraps a single `authority_scope` string into a list before passing to `append_hermes_summary()`. The spine function expects `list`. This works but the type mismatch (`str` in adapter, `list` in spine) is implicit.

### Idempotence

Hermes pairing is idempotent by hermes_id — re-pairing returns the existing record. This is correct. However, it also means a re-pair cannot change the device_name or refresh the token expiration. May need an explicit re-pair/renew flow later.

### Replay and Re-entry

Authority tokens have no nonce or jti. Token reuse is indistinguishable from legitimate use. For LAN-only milestone 1, this is acceptable. Summary appends are append-only with unique UUIDs, so replaying an append creates a duplicate event, not a state corruption.

## Milestone Fit

| Plan Task | Status | Notes |
|-----------|--------|-------|
| Create hermes.py adapter module | Done | All functions implemented |
| HermesConnection with authority token validation | Done | `connect()` validates JSON tokens; header auth uses pairing lookup |
| readStatus through adapter | Done | Capability-gated, delegates to `miner.get_snapshot()` |
| appendSummary through adapter | Done | Capability-gated, writes to spine |
| Event filtering (block user_message) | Done | `HERMES_READABLE_EVENTS` allowlist enforced |
| Hermes pairing endpoint | Done | `POST /hermes/pair` with idempotence |
| Update CLI with Hermes subcommands | Not done | Not in this slice |
| Update gateway client Agent tab | Not done | Not in this slice |
| Write tests | Not done | Not in this slice |

Plan milestones 1-2 are substantially complete. Milestones 3-4 (client update, tests) remain.

## Remaining Blockers

### Must-fix before lane completion

1. **Control endpoint protection.** The plan's acceptance criteria include "Hermes CANNOT issue control commands (403)". Currently `/miner/start` accepts any caller. Either add Hermes-rejection logic to control endpoints, or revise the acceptance criteria to acknowledge that control endpoints are unauthenticated in milestone 1.

### Should-fix before next milestone

2. **Pairing approval flow.** The reference spec implies a pairing flow; the implementation auto-approves. The emitted `PAIRING_REQUESTED` / `PAIRING_GRANTED` events are cosmetic — no approval decision happens between them.

3. **Token signing.** Authority tokens are unsigned JSON. Before any network exposure beyond LAN, tokens need HMAC or asymmetric signing.

4. **`/hermes/pairings` auth.** Listing pairings should require at minimum gateway device auth.

## Verdict

**CONDITIONALLY APPROVED.**

The adapter's domain model, capability enforcement, event filtering, and pairing lifecycle are correct and aligned with the reference contract. Three bugs were fixed during review. The code loads cleanly and the adapter functions work as specified.

The condition: the control-endpoint gap (blocker #1 above) must be addressed — either by adding a Hermes guard to `/miner/*` endpoints or by explicitly documenting in the plan that Hermes control rejection is deferred to when device auth lands. The current plan acceptance criteria cannot be met without one of these.

Next steps: tests (plan milestone 4), Agent tab update (plan milestone 3), then address the security items before any network-facing deployment.
