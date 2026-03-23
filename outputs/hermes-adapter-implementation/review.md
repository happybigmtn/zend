# Hermes Adapter — Honest Review

**Lane:** `hermes-adapter-implementation`
**Status:** blocked
**Date:** 2026-03-22
**Updated:** 2026-03-23 (polish pass)

---

## Verdict

This is a useful first slice. Core adapter shape is correct: Hermes can observe miner status, append summaries, and read filtered events. The control-block is verified. However, the trust boundary is weaker than the plan requires. Three honest gaps block sign-off.

---

## Finding 1 — Critical: Hermes runtime auth is keyed by `hermes_id`, not the authority token

**Claim vs. reality:** The slice promises authority-token validation. Runtime requests (`/hermes/status`, `/hermes/summary`, `/hermes/events`) actually authorize with `Authorization: Hermes <hermes_id>` alone.

**Evidence:**
- `hermes.validate_hermes_auth()` accepts only a `hermes_id` and never touches a token.
- Daemon endpoints call `validate_hermes_auth(hermes_id)` and never pass a token.
- `hermes.connect(authority_token)` is the only path that checks the token, and it is not called by any runtime endpoint.

**Impact:** Any caller who knows a paired `hermes_id` can read status, append summaries, and read filtered events — no token required. This is a meaningful gap if Hermes credentials ever travel beyond a trusted LAN.

**Fix options:**
- **Option A (strong):** Make runtime endpoints require a server-issued session derived from the token (e.g., a signed session cookie or short-lived bearer). Token is consumed at `connect()` and a session is returned for subsequent calls.
- **Option B (documented-weak):** Change the spec to document that Hermes auth is ID-based after pairing, and treat the token as a pairing credential only (used once at `connect()`). This must be an explicit design decision, not an oversight.

**Recommendation:** Option A, but it requires a spec change before implementation.

---

## Finding 2 — High: Token expiration is malformed at issuance and unenforced at runtime

**Evidence:**
- `pair_hermes()` writes: `token_expires_at = datetime.now(timezone.utc).isoformat()` — token expires at the moment of creation.
- `connect()` reads `token_expires_at` from the pairing record but never compares it against the current time.
- Confirmed state from review run: `paired_at` and `token_expires_at` are within 5 microseconds of each other.

**Impact:** Expiration cannot serve as a revocation or rotation mechanism. An old token and a new token are indistinguishable to `connect()`.

**Fix options:**
- If tokens should expire: issue a real future timestamp (e.g., +30 days) and add `datetime.now(timezone.utc) >= token_expires_at` check in `connect()`.
- If tokens should not expire: remove `token_expires_at` from `HermesPairing` and the store schema.

---

## Finding 3 — Medium: Planned boundary tests are absent

**Evidence:**
- `services/home-miner-daemon/tests/test_hermes.py` does not exist.
- `pytest services/home-miner-daemon/tests/test_hermes.py -v` fails with file-not-found.

**What tests must cover:**
1. Token issuance and validation (valid token → connection; invalid token → `ValueError`)
2. Capability enforcement (`observe` required for `read_status`, `summarize` required for `append_summary`)
3. `user_message` filtering (injected `user_message` event does not appear in `get_filtered_events` results)
4. Hermes control-block (`POST /miner/start` with Hermes auth → 403)
5. Idempotent pairing (calling `pair_hermes` twice with same `hermes_id` → same token)

---

## Fix Applied During Review

**Problem:** A duplicate `do_POST()` method definition in `services/home-miner-daemon/daemon.py` was shadowing the primary handler, disabling all Hermes routing except for what appeared in the second (active) definition.

**Result after removal:** All five Hermes endpoints are active. Control-block with Hermes auth returns `403`.

**Note on current daemon.py state:** The file is now clean. The duplicate was removed and routing is correct. The `get_hermes_module()` lazy-import pattern successfully avoids circular imports.

---

## What Works

- `services/home-miner-daemon/hermes.py` module with correct adapter-shaped functions.
- `POST /hermes/pair` creates idempotent pairing with `observe` + `summarize`.
- `read_status()` correctly delegates to `miner.get_snapshot()`.
- `append_summary()` correctly appends `HERMES_SUMMARY` events to the spine.
- `get_filtered_events()` correctly omits `user_message` in the reviewed flow.
- Control endpoints correctly reject Hermes auth with `403`.

---

## Supervisory Action Items

| Priority | Action | Owner |
|----------|--------|-------|
| **Before any downstream work** | Resolve Finding 1: decide between Option A (session-based) or Option B (document ID-based auth) at the spec level | spec owner |
| **Before sign-off** | Implement token expiration fix (Finding 2) or explicitly remove the field | implementer |
| **Before sign-off** | Add `tests/test_hermes.py` with the five coverage areas above | implementer |
| **Optional** | Consider adding a `GET /hermes/connection_status` that returns the token expiry and last-connect time for diagnostics | implementer |

---

## Verification Environment

Isolated daemon run with `ZEND_STATE_DIR` and `ZEND_BIND_PORT=18080`. All endpoint behaviors confirmed via direct HTTP requests against the running server.
