# Hermes Adapter Implementation — Review

**Lane:** hermes-adapter-implementation
**Reviewer:** Nemesis-style security review
**Date:** 2026-03-22
**Verdict:** CONDITIONAL PASS — Milestone 1 fit, with fixes applied and documented blockers for production

## Summary

The Hermes adapter implements the correct capability boundary for milestone 1. After three source fixes applied during this review, the adapter enforces its contract: observe-only reads, summarize-only writes, user_message filtering, and capability ceiling validation. The implementation is suitable for LAN-only local development. It is NOT suitable for any deployment beyond localhost without addressing the security items below.

## Fixes Applied During Review

Three correctness issues were fixed in-place (within touched surfaces):

### Fix 1: Missing observe capability check in get_filtered_events

**File:** `hermes.py:332`
**Before:** `get_filtered_events()` performed event-kind filtering but no capability check. A HermesConnection with only `summarize` could read events.
**After:** Added `observe` capability check, consistent with `read_status()`.

### Fix 2: Dead assignment and inline import in issue_hermes_token

**File:** `hermes.py:161-165`
**Before:** `expires = now.replace(microsecond=0)` was immediately overwritten. `from datetime import timedelta` was imported inside the function body.
**After:** Removed dead assignment. Moved `timedelta` to module-level import.

### Fix 3: Write-only _hermes_connections cache removed

**File:** `daemon.py:154-179`
**Before:** `_hermes_connections` dict was written to on every request (lines 179, 290) but never read. Unbounded memory growth in long-running daemon.
**After:** Removed the dict and all writes. Each request validates tokens freshly via `_hermes.connect()`, which is the correct behavior (no stale cached connections).

## Nemesis Pass 1 — First-Principles Trust Boundary Challenge

### Q: Who can trigger dangerous actions through this adapter?

**Token forgery:** Any process on the local machine. Tokens are unsigned base64-JSON. An attacker with filesystem access to `state/` can read stored tokens; any process that can reach the daemon's port can forge tokens with arbitrary capabilities.

**Mitigated by:** LAN-only binding (127.0.0.1), capability ceiling in `connect()` rejects non-Hermes capabilities even if forged.

**Verdict:** Acceptable for milestone 1 (localhost simulator). Blocks production deployment.

### Q: Can Hermes escalate to control?

Two paths checked:

1. **Via adapter:** `connect()` at hermes.py:264 validates `cap in HERMES_CAPABILITIES`. A token claiming `control` is rejected. **Blocked.**

2. **Via HTTP bypass:** Hermes omits `Authorization: Hermes` header and calls `/miner/start` directly. The control endpoints have no general auth — they're open to any caller that reaches the port. **Not blocked by the adapter**, but mitigated by network binding (127.0.0.1 only).

**Verdict:** The adapter's capability ceiling holds. The HTTP-layer bypass is a known gap acceptable for milestone 1. Production requires unified auth middleware.

### Q: Can Hermes read user messages?

`get_filtered_events()` filters to `HERMES_READABLE_EVENTS` which excludes `user_message`. The filter operates on `SpineEvent.kind` string comparison. **Blocked.**

Note: the reference spec says "Read-only access to user messages" as a boundary. The implementation is stricter — it blocks user_message reads entirely. This is a deliberate tightening documented in the spec artifact.

### Q: Can Hermes write arbitrary event types?

`append_summary()` hardcodes `EventKind.HERMES_SUMMARY` via `spine.append_hermes_summary()`. Hermes cannot choose the event kind. **Blocked.**

### Q: What happens with expired tokens?

`connect()` checks `token.is_expired()` on every call. Since there's no connection caching (removed in Fix 3), every HTTP request re-validates. **Expiry is enforced per-request.**

## Nemesis Pass 2 — Coupled-State and Protocol Surface Review

### Token ↔ Pairing state coupling

**Issue:** `pair_hermes()` is idempotent — re-pairing returns the existing record without re-issuing a token. But the `/hermes/pair` endpoint always issues a fresh token regardless of whether the pairing was new or idempotent. This means re-pairing generates a new token while the old token remains valid until expiry.

**Impact:** Multiple valid tokens can exist simultaneously for the same hermes_id. Not a correctness issue (each token is independently validated), but worth noting for audit.

### Pairing store ↔ Token store coherence

Pairing records live in `hermes-store.json`. Tokens are persisted separately as `hermes_token_{id}.json` by the CLI. There is no mechanism to revoke a pairing's token — deleting the pairing record doesn't invalidate outstanding tokens because `connect()` validates token structure and expiry, not pairing existence.

**Impact:** Token revocation requires waiting for expiry. No immediate revocation path exists.

**Verdict:** Acceptable for milestone 1 (24h TTL). Production requires a revocation list or short-lived tokens + refresh flow.

### Event spine append safety

`append_summary()` delegates to `spine.append_hermes_summary()` which calls `spine.append_event()`. The spine is append-only (file append mode `'a'`). No mutation or deletion path exists. **Safe.**

Summary payload is caller-controlled (`summary_text`, `authority_scope`). No size validation. A Hermes agent could append arbitrarily large summaries.

**Impact:** Disk exhaustion on long-running daemon. Low risk for milestone 1 (local dev).

### Replay / Nonce

`HermesAuthorityToken.nonce` is generated at issuance (uuid4) but never checked at `connect()`. The same token can be replayed indefinitely within its TTL window.

**Impact:** If a token is intercepted (logged, network capture on non-localhost deployment), it grants full Hermes access until expiry. Mitigated by localhost binding and 24h TTL.

### Thread safety

`daemon.py` uses `ThreadedHTTPServer`. `hermes.py` reads/writes `hermes-store.json` without locking. Concurrent `/hermes/pair` calls could race on file read-modify-write.

**Impact:** Corrupted pairing store under concurrent pairing. Low probability in milestone 1 (single user, infrequent pairing). Production requires file locking or database.

## Milestone Fit Assessment

### Plan tasks covered

| Plan Task | Status | Evidence |
|-----------|--------|----------|
| Create hermes.py adapter module | Done | hermes.py: 380 lines |
| HermesConnection with authority token validation | Done | connect() with expiry + capability checks |
| readStatus through adapter | Done | read_status() + GET /hermes/status |
| appendSummary through adapter | Done | append_summary() + POST /hermes/summary |
| Event filtering (block user_message) | Done | get_filtered_events() with HERMES_READABLE_EVENTS |
| Hermes pairing endpoint | Done | POST /hermes/pair |
| CLI with Hermes subcommands | Done | 5 subcommands: pair, connect, status, summary, events |
| Gateway client Agent tab update | Not started | Milestone 3 per plan |
| Tests for adapter boundary | Not started | Milestone 4 per plan |

### Milestones 1-2 complete. Milestones 3-4 remain.

## Remaining Blockers

### Before Milestone 3 (Gateway Client Update)
- No blockers. Requires frontend work in `apps/zend-home-gateway/index.html`.

### Before Milestone 4 (Tests)
- No blockers. Test infrastructure does not exist yet but pytest is sufficient.

### Before Production Deployment (NOT milestone 1)
1. **Token signing** — Replace base64 encoding with HMAC-SHA256 or JWT. Depends on plan 006 (token auth).
2. **Nonce validation** — Implement nonce cache, reject replayed tokens.
3. **Token revocation** — Either short-lived tokens with refresh, or explicit revocation list.
4. **Payload redaction** — Strip sensitive fields from `control_receipt` before returning to Hermes.
5. **Unified auth middleware** — Replace per-endpoint string-prefix checks with capability-based routing.
6. **File locking** — Hermes store concurrent access protection.
7. **Summary size limits** — Bound `summary_text` length to prevent disk exhaustion.
8. **Token file permissions** — Set 0600 on `hermes_token_*.json` files.

## Security Summary Table

| Finding | Severity | Milestone 1 | Production |
|---------|----------|-------------|------------|
| Unsigned tokens | Critical | Acceptable (localhost) | Must fix |
| No replay protection | Critical | Acceptable (localhost) | Must fix |
| Plaintext token storage | High | Acceptable (local files) | Must fix |
| No payload redaction | Medium | Acceptable (known limitation) | Must fix |
| String-prefix control denial | Medium | Acceptable (localhost) | Must fix |
| No summary size limit | Low | Acceptable (local dev) | Should fix |
| No pairing audit event | Low | Acceptable | Should fix |
| File-level race on pairing store | Low | Acceptable (single user) | Should fix |
| Empty capability list accepted | Low | No practical impact | Should fix |

## Verdict

**CONDITIONAL PASS for milestone 1.**

The adapter correctly enforces its capability ceiling, event filtering, and capability-scoped access. The three fixes applied during this review closed real gaps (missing observe check, memory leak, dead code). The remaining security items are explicitly scoped to pre-production work and depend on upstream plans (006 token auth, 007 observability).

The lane is unblocked for milestones 3-4 work.
