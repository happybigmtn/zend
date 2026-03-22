# Hermes Adapter Implementation — Nemesis Review

**Status:** Reviewed with fixes applied
**Reviewer:** Nemesis pass (first-principles + coupled-state)
**Date:** 2026-03-22
**Test evidence:** 24/24 passing (up from 21 — 3 new boundary tests added)

## Verdict

**CONDITIONALLY APPROVED** — The core capability boundary model is sound after three fixes applied during review. The adapter correctly enforces the observe/summarize scope, filters events by allowlist, and rejects control commands. Remaining issues are documented below as known limitations acceptable for milestone 1.

## Fixes Applied During Review

### Fix 1: Missing observe capability check on event reads (CRITICAL)

`get_filtered_events()` did not verify the connection holds the `observe` capability. A token minted with only `summarize` could read the filtered event spine. This violated the adapter's own security model — every action must verify its required capability at point-of-use.

**File:** `hermes.py:get_filtered_events()` — added `PermissionError` guard
**Test:** `TestEventFilteringRequiresObserve::test_filtered_events_without_observe_raises`

### Fix 2: hermes_id injection via pipe delimiter

`pair_hermes()` accepted arbitrary `hermes_id` values including pipe `|` characters. Since the authority token format is `hermes_id|principal_id|caps|expiry`, a pipe in hermes_id produces a malformed token (5+ segments). The pairing record is created but the token is permanently unusable — a silent failure that leaves dead state.

**File:** `hermes.py:pair_hermes()` — added input validation
**Test:** `TestHermesIdValidation::test_pipe_in_hermes_id_rejected`

### Fix 3: Stale token on idempotent re-pair

`pair_hermes()` idempotent path returned cached connection data without checking token expiry. After 30-day token expiration, calling `pair_hermes()` again with the same hermes_id returned a connection object, but all subsequent operations would fail because the stored token was expired. The re-pair path now regenerates the token if expired.

**File:** `hermes.py:pair_hermes()` — added expiry check + token regeneration
**Test:** `TestExpiredRepair::test_repairing_expired_regenerates_token`

## Nemesis Pass 1 — Trust Boundaries & Authority

### What's correct

| Property | Evidence |
|----------|----------|
| Capability set is hardcoded constant | `HERMES_CAPABILITIES = ['observe', 'summarize']` — not derived from user input |
| Event filter uses allowlist | `HERMES_READABLE_EVENTS` explicitly enumerates readable kinds; new event types are excluded by default |
| Capability checked at action time | `read_status()`, `append_summary()`, `get_filtered_events()` each verify capability independently |
| Control endpoints reject Hermes auth | `daemon.py:286-289` checks `_parse_hermes_auth()` on all control POST paths, returns 403 |
| Token validation checks expiry | `_validate_authority_token()` compares against `datetime.now(timezone.utc)` |
| Token validation checks capabilities against allowlist | Each cap in token validated against `HERMES_CAPABILITIES` |

### Known limitations (acceptable for M1, LAN-only)

1. **Plaintext tokens in pairing store.** Authority tokens are stored verbatim in `pairing-store.json`. Any process with filesystem read access can extract and replay them. Acceptable because the daemon binds 127.0.0.1 and the threat model assumes local trust in M1.

2. **No token signing/HMAC.** Token format is `hermes_id|principal_id|caps|expiry` — all cleartext, no signature. A synthetic token with valid format and future expiry would be accepted by `connect()`. The daemon mitigates this by always looking up the stored token by hermes_id rather than accepting arbitrary bearer tokens, but the `connect()` function itself has no forgery protection.

3. **Bearer-by-name auth model.** The HTTP header `Authorization: Hermes <hermes_id>` transmits only the hermes_id, not the token. The daemon looks up the token server-side. This means knowing a hermes_id is sufficient to authenticate — there is no client-side secret. Acceptable for LAN-only M1.

4. **No rate limiting.** Unlimited pairing and summary-append operations. A local process could flood the event spine.

5. **No input size limits on summary_text.** Hermes can append arbitrarily large summaries to the spine.

## Nemesis Pass 2 — Coupled State & Protocol Surfaces

### Shared pairing store schema divergence

Hermes records and device records coexist in `pairing-store.json` with different schemas:

| Field | Device record | Hermes record |
|-------|--------------|---------------|
| `hermes_id` | absent | present |
| `authority_token` | absent | present |
| `token_expires_at` | ISO timestamp (creation time) | ISO timestamp (30 days out) |
| `capabilities` | `['observe']` or `['observe','control']` | `['observe','summarize']` |
| `device_name` | user-provided | `hermes-{hermes_id}` |

**Risk:** `store.has_capability()` searches by `device_name`. A Hermes record with `device_name="hermes-hermes-001"` is findable by `has_capability("hermes-hermes-001", "observe")` → True. This doesn't escalate privileges in M1 (no HTTP auth on regular endpoints) but creates a latent cross-path if device auth is added later.

**Recommendation:** Future milestone should prefix Hermes device_names with a reserved namespace or use a separate store.

### Event spine asymmetry

Hermes pairing emits `PAIRING_REQUESTED` but not `PAIRING_GRANTED`. Regular device pairing (via `cli.py`) emits both. This means the audit trail for Hermes pairings is incomplete — a spine reader cannot distinguish a pending Hermes pairing request from a completed one.

**Recommendation:** Emit `PAIRING_GRANTED` after Hermes pairing succeeds, with `agent_type: "hermes"` in payload.

### hermes_summary payload spec drift

The `event-spine.md` spec defines `hermes_summary` payload as:
```
{ summary_text: string, authority_scope: ('observe' | 'control')[], generated_at: string }
```

The implementation:
- Adds `hermes_id` field (not in spec)
- Passes `authority_scope` as connection capabilities which may include `'summarize'` — a value not in the spec's enum

Neither is a runtime error, but the spine contract and implementation have diverged.

### Concurrent write safety

`pairing-store.json` is read-modify-write without file locking. The daemon uses `ThreadedHTTPServer`. Two simultaneous `/hermes/pair` requests could cause a lost-update race. The event spine uses append-only writes, which is safer but still not atomic (no `flock`). Acceptable for M1 single-user scenario.

## Test Coverage Assessment

| Boundary | Tested | Test |
|----------|--------|------|
| Capability constants | Yes | `TestHermesCapabilities` |
| Valid token accepted | Yes | `TestTokenValidation::test_valid_token_parses` |
| Empty token rejected | Yes | `TestTokenValidation::test_empty_token_rejected` |
| Malformed token rejected | Yes | `TestTokenValidation::test_malformed_token_rejected` |
| Expired token rejected | Yes | `TestTokenValidation::test_expired_token_rejected` |
| Connect lifecycle | Yes | `TestHermesConnection` |
| Pairing creation | Yes | `TestHermesPairing::test_pair_hermes_creates_record` |
| Pairing idempotence | Yes | `TestHermesPairing::test_pair_hermes_idempotent` |
| Token retrieval | Yes | `TestHermesPairing::test_get_authority_token` |
| Status read with observe | Yes | `TestReadStatus::test_read_status_with_observe` |
| Status read without observe | Yes | `TestReadStatus::test_read_status_without_observe` |
| Summary append with summarize | Yes | `TestAppendSummary::test_append_summary_with_summarize` |
| Summary append without summarize | Yes | `TestAppendSummary::test_append_summary_without_summarize` |
| Summary appears in spine | Yes | `TestAppendSummary::test_summary_appears_in_spine` |
| Event filter excludes user_message | Yes | `TestEventFiltering` |
| Event filter requires observe | Yes | `TestEventFilteringRequiresObserve` (NEW) |
| hermes_id pipe injection | Yes | `TestHermesIdValidation` (NEW) |
| Expired re-pair regenerates token | Yes | `TestExpiredRepair` (NEW) |
| No control capability | Yes | `TestNoControlCapability` |
| Summary event format | Yes | `TestObservability` |

### Not tested (integration-level)

- Live daemon HTTP endpoints for Hermes
- Hermes auth header rejection on control endpoints via HTTP
- Concurrent pairing race conditions
- Smoke test script execution against running daemon
- Gateway client Agent tab rendering

## Milestone Fit

The implementation covers plan milestones 1 (adapter module) and 2 (daemon endpoints) plus CLI subcommands. Milestone 3 (Agent tab update) and milestone 4 (integration tests) remain.

### Frontier tasks status

| Task | Status |
|------|--------|
| Create hermes.py adapter module | Done |
| Implement HermesConnection with authority token validation | Done |
| Implement readStatus through adapter | Done |
| Implement appendSummary through adapter | Done |
| Implement event filtering (block user_message events) | Done |
| Add Hermes pairing endpoint to daemon | Done |
| Update CLI with Hermes subcommands | Done |
| Update gateway client Agent tab | Not started |

## Remaining Blockers

1. **Agent tab not wired** — The gateway client `index.html` still shows "Hermes not connected" placeholder. No JavaScript calls the `/hermes/*` endpoints.

2. **Integration test gap** — All tests are unit-level. No test starts the daemon and exercises the HTTP layer end-to-end.

3. **Smoke script outdated** — `scripts/hermes_summary_smoke.sh` writes directly to the spine, bypassing the adapter. It should be updated to use the HTTP endpoints.

4. **Spec coordination needed** — `event-spine.md` payload schema for `hermes_summary` doesn't include `hermes_id` or `summarize` in authority_scope enum. Either the spec or implementation should be updated to match.

## Validation

```
$ ZEND_STATE_DIR=$(mktemp -d) python3 -m pytest tests/test_hermes.py -v
24 passed in 0.04s
```
