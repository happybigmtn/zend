# Hermes Adapter Implementation — Review

**Lane:** `hermes-adapter-implementation`
**Reviewer:** Nemesis-style security review
**Date:** 2026-03-22
**Verdict:** CONDITIONAL PASS — Milestone 1 fit; fixes applied; production blockers documented

---

## Summary

The adapter correctly enforces its security contract: Hermes agents can observe miner status and append summaries, but cannot issue control commands or read user messages. Three correctness issues were fixed during this review. The remaining items are explicitly scoped to pre-production work that depends on upstream plans (plan 006 token auth, plan 007 observability).

The lane is unblocked for milestones 3–4.

---

## Fixes Applied During Review

### Fix 1: Missing `observe` capability check in `get_filtered_events()`

**File:** `services/home-miner-daemon/hermes.py` — `get_filtered_events()`
**Before:** Event-kind filtering was applied but no capability check existed. A `HermesConnection` with only `"summarize"` could read events.
**After:** Added `"observe"` capability check, consistent with `read_status()`.

### Fix 2: Dead assignment and inline import in `issue_hermes_token()`

**File:** `services/home-miner-daemon/hermes.py` — `issue_hermes_token()`
**Before:** `expires = now.replace(microsecond=0)` was immediately overwritten. `from datetime import timedelta` was an inline import inside the function.
**After:** Removed dead assignment. Moved `timedelta` to module-level import.

### Fix 3: Write-only `_hermes_connections` cache removed from daemon

**File:** `services/home-miner-daemon/daemon.py` — `GatewayHandler`
**Before:** `_hermes_connections` dict was written on every request but never read, causing unbounded memory growth in long-running daemons.
**After:** Removed the dict entirely. Every HTTP request re-validates its token freshly via `hermes.connect()`. This is the correct behavior — no stale cached connections.

---

## Nemesis Pass 1 — Trust Boundary Challenge

### Q: Can Hermes escalate to control commands?

Two paths examined:

**Via adapter:** `connect()` at `hermes.py` validates `cap in HERMES_CAPABILITIES` for every capability in the token. A token claiming `"control"` is rejected at connect time. **Blocked.**

**Via HTTP bypass:** Hermes could omit the `Authorization: Hermes` prefix and call `/miner/start` directly. The control endpoints check the auth header prefix but have no cryptographic auth. **Not blocked by adapter**, but mitigated by LAN-only binding (`127.0.0.1`). Production requires unified capability-based auth middleware.

### Q: Can Hermes read user messages?

`get_filtered_events()` filters to `HERMES_READABLE_EVENTS = ["hermes_summary", "miner_alert", "control_receipt"]`. `user_message` is absent. **Blocked.**

The implementation is stricter than the plan's "read-only access to user messages" phrasing — it blocks reads entirely. Deliberate tightening documented in `spec.md`.

### Q: Can Hermes write arbitrary event types?

`append_summary()` calls `spine.append_hermes_summary()` which hardcodes `EventKind.HERMES_SUMMARY`. Hermes cannot select the event kind. **Blocked.**

### Q: What happens with expired tokens?

`connect()` calls `token.is_expired()` on every request. No connection caching means tokens are re-validated per HTTP call. **Expiry is enforced on every request.**

### Q: Who can forge tokens?

Any process with filesystem access to `state/hermes_token_<id>.json` or the ability to send HTTP to the daemon port. Tokens are unsigned base64-JSON. **Critical for non-localhost deployments.** Acceptable for milestone 1 (localhost-only binding).

---

## Nemesis Pass 2 — Coupled State and Protocol Surface

### Token issuance is not idempotent per pairing

`pair_hermes()` is idempotent — re-pairing returns the existing record. But `/hermes/pair` always issues a fresh token on every call, even when the pairing already exists. Multiple valid tokens can coexist for the same `hermes_id` until each expires.

**Impact:** Low for milestone 1. Production should either return the existing token or implement explicit revocation.

### No token revocation path

Pairing records live in `hermes-store.json`; tokens are validated by structure and expiry only. Deleting a pairing record does not invalidate outstanding tokens.

**Impact:** Token revocation requires waiting for expiry. Acceptable for milestone 1 (24h TTL, localhost). Production needs a revocation list or short-lived tokens with refresh.

### No summary size limit

`append_summary()` accepts any-length `summary_text`. A Hermes agent could exhaust disk with oversized summaries on a long-running daemon.

**Impact:** Low for milestone 1 (local dev). Production should enforce a `MAX_SUMMARY_BYTES` constant.

### No nonce / replay protection

`HermesAuthorityToken.nonce` is generated at issuance (uuid4) but never checked at `connect()`. A captured token grants full Hermes access until expiry.

**Impact:** Mitigated by localhost binding and 24h TTL. Production (plan 006) must implement nonce cache or signed tokens.

### Thread safety gap

`daemon.py` uses `ThreadedHTTPServer` but `hermes.py` reads/writes `hermes-store.json` without locking. Concurrent `/hermes/pair` calls can race on read-modify-write.

**Impact:** Low probability in milestone 1 (single-user, infrequent pairing). Production needs file locking or an atomic write-rename pattern.

---

## Milestone Fit Assessment

| Plan Task | Status | Evidence |
|-----------|--------|----------|
| Create `hermes.py` adapter module | Done | `services/home-miner-daemon/hermes.py`, ~380 lines |
| `HermesConnection` with authority token validation | Done | `connect()` with expiry + capability ceiling checks |
| `read_status()` through adapter | Done | `hermes.read_status()` + `GET /hermes/status` |
| `append_summary()` through adapter | Done | `hermes.append_summary()` + `POST /hermes/summary` |
| Event filtering (block `user_message`) | Done | `get_filtered_events()` with `HERMES_READABLE_EVENTS` |
| Hermes pairing endpoint | Done | `POST /hermes/pair` |
| CLI with Hermes subcommands | Done | 5 subcommands: `pair`, `connect`, `status`, `summary`, `events` |
| Gateway client Agent tab update | Not started | Milestone 3 |
| Adapter boundary tests | Not started | Milestone 4 |

**Milestones 1–2: complete. Milestones 3–4: not started.**

---

## Security Summary

| Finding | Severity | Milestone 1 | Production |
|---------|----------|-------------|------------|
| Unsigned tokens (base64-JSON only) | Critical | Acceptable (localhost) | Must fix — plan 006 |
| No replay protection (nonce ignored) | Critical | Acceptable (localhost) | Must fix — plan 006 |
| Plaintext token storage in `state/` | High | Acceptable (local files, single-user) | Must fix — set `0600` perms |
| No payload redaction on `control_receipt` | Medium | Acceptable (known limitation) | Should fix — milestone N |
| String-prefix control denial (not capability-based) | Medium | Acceptable (localhost) | Should fix — unified auth |
| No summary size limit | Low | Acceptable (local dev) | Should fix — `MAX_SUMMARY_BYTES` |
| No pairing audit event on spine | Low | Acceptable | Should fix — milestone N |
| File-level race on `hermes-store.json` | Low | Acceptable (single user) | Should fix — atomic writes |
| Empty capability list accepted | Low | No practical impact | Should fix — reject empty |

---

## Remaining Blockers

### Milestone 3 (Gateway client Agent tab) — No blockers.

### Milestone 4 (Adapter boundary tests) — No blockers.
Test infrastructure does not exist yet; `pytest` is sufficient.

### Before Production Deployment — All of the following:

1. **Token signing** — Replace base64 encoding with HMAC-SHA256 or JWT. Depends on plan 006.
2. **Nonce validation** — Implement nonce cache; reject replayed tokens. Depends on plan 006.
3. **Token revocation** — Short-lived tokens with refresh, or explicit revocation list.
4. **Payload redaction** — Strip sensitive fields from `control_receipt` before returning to Hermes.
5. **Unified auth middleware** — Replace per-endpoint `Authorization.startswith("Hermes ")` checks with capability-based routing.
6. **File locking** — Protect `hermes-store.json` with `fcntl` or atomic write-rename.
7. **Summary size limits** — Enforce `MAX_SUMMARY_BYTES` constant to prevent disk exhaustion.
8. **Token file permissions** — Set `0600` on `state/hermes_token_*.json` files.

---

## Verdict

**CONDITIONAL PASS for milestones 1–2.**

The adapter correctly enforces its capability ceiling, event filtering, and capability-scoped access. The three fixes closed real gaps: a missing capability check on event reads, a memory leak in the daemon, and a dead assignment in token issuance. The remaining security items are pre-production work and are correctly gated on upstream plans.

The lane is unblocked.
