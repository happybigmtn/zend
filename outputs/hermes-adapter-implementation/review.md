# Hermes Adapter Implementation Review

**Review Date:** 2026-03-22
**Reviewer:** Nemesis Security Review
**Status:** CONDITIONAL APPROVAL — two critical findings require remediation

## Verdict

The capability boundary logic is correct and the milestone 1 functional requirements are met. The adapter properly scopes Hermes to observe + summarize, blocks control endpoints with double-layer defense, and filters events by whitelist. However, the **authentication model has two critical gaps** that undermine the capability boundary: token leakage via idempotent pairing (C1) and post-connect auth that doesn't require the token (C2). These must be fixed before this slice is considered secure.

**Recommendation:** Fix C1 and C2 before merge. All other findings are acceptable for MVP with tracking.

---

## Critical Findings (Must Fix Before Merge)

### C1 — Idempotent pairing leaks existing tokens

**File:** `hermes.py:133-134`, `daemon.py:257-264`

When `pair_hermes()` is called with an existing `hermes_id`, it returns the full `HermesPairing` including the secret token. The daemon endpoint then returns this token in the JSON response. Any caller who knows or guesses a `hermes_id` can retrieve its token by calling `/hermes/pair`.

**Impact:** Token disclosure. Attacker who can reach `/hermes/pair` can steal any Hermes agent's token.

**Fix:** On re-pair, return pairing metadata without the token. Or reject re-pair with `409 Conflict`.

### C2 — Post-connect auth uses only hermes_id, no token

**File:** `daemon.py:167-177`, `hermes.py:311-330`

After `/hermes/connect` validates the token once, all subsequent requests use `Authorization: Hermes <hermes_id>` — the token is not required. `_get_hermes_connection()` looks up only the hermes_id in the in-memory dict.

**Impact:** Any process that knows a hermes_id (which is user-chosen, not secret) can impersonate a connected Hermes agent.

**Fix:** Either require `Hermes <hermes_id>:<token>` on every request, or issue a session token at connect time.

---

## High Findings (Should Fix Before Merge)

### H1 — `/hermes/pair` is fully unauthenticated

**File:** `daemon.py:249-267`

No authentication is required to create a Hermes pairing. Combined with C1, any process that can reach the daemon gets full Hermes access. Bounded by localhost default, but `ZEND_BIND_HOST` is configurable.

**Fix:** Require principal/owner authentication, or implement a pairing approval flow.

### H2 — `token_expires_at` is set to creation time

**File:** `hermes.py:145`

`token_expires_at=datetime.now(timezone.utc).isoformat()` sets expiration to *now*, not a future time. The field is never checked in `connect()`. If expiration were ever enforced, all tokens would fail immediately.

**Fix:** Set to a real future time and enforce in `connect()`, or remove the field.

### H3 — `import os` after use

**File:** `hermes.py:115, 122`

`os.environ` is referenced at line 115 inside `_get_hermes_pairings_file()`, but `import os` appears at line 122. This works because Python evaluates function bodies at call time, not definition time, and all module-level imports complete before any function is called. But it's fragile and confusing.

**Fix:** Move `import os` to the top of the file with other imports.

---

## Medium Findings (Track for Post-Merge)

### M1 — No Hermes revocation mechanism

No `unpair_hermes()` or token invalidation exists. Once paired, a Hermes agent has permanent access until the daemon restarts AND `hermes-pairings.json` is manually edited. The `capability_revoked` event kind exists in the spine but is never emitted by the Hermes adapter.

### M2 — No rate limiting or size limits on summary append

`append_summary()` has no rate limiting, deduplication, or size limit on `summary_text`. A misbehaving Hermes agent can flood the event spine.

### M3 — In-memory connection state never expires

`_hermes_connections` dict in `daemon.py:164` grows monotonically. No TTL, no cleanup, no connection limit. If a pairing is deleted from disk, the in-memory connection remains valid.

### M4 — Hermes summaries use system principal_id

`hermes.py:251-255` — Hermes events are attributed to the same `principal_id` as user-initiated events. The `kind` field is the only discriminator. Consider adding `hermes_id` to the summary payload.

### M5 — Broad exception catch leaks internals

`daemon.py:265-266` — `except Exception as e: self._send_json(500, {"error": str(e)})` can expose file paths, module names, and internal state in error responses.

### M6 — JSON file writes are not atomic

`hermes.py:108-109` — `_save_hermes_pairings()` writes directly to the file. A crash mid-write corrupts the pairing store. Use write-to-temp + `os.rename()`.

---

## Low / Informational

### L1 — Event filter may return fewer than `limit` results

`hermes.py:275` over-fetches by 2x, but if the spine is dominated by non-readable events, fewer than `limit` results are returned. The 2x multiplier is an arbitrary heuristic.

### L2 — Reference contract divergence on user_message

`references/hermes-adapter.md:74` says "Read-only access to user messages." Implementation blocks `USER_MESSAGE` entirely. This is more restrictive (safer) but is an undocumented divergence from the reference contract.

### L3 — Three separate Hermes state files

Hermes state is split across `hermes-pairings.json` (adapter), `_hermes_connections` (in-memory), and `hermes-cli-state.json` (CLI). No unified view.

### L4 — State files are world-readable by default

`hermes-pairings.json` and `hermes-cli-state.json` contain bearer tokens with default umask (typically 0644). Acceptable for single-user home miner, but should be tightened for production.

### L5 — No CORS or origin validation

If daemon is bound to a non-localhost address, browser-based CSRF attacks could trigger pairing or connection from a malicious webpage.

### L6 — Hermes connect/disconnect not audited in spine

No spine event is emitted when a Hermes agent connects or disconnects. The operator has no visibility into Hermes session lifecycle.

---

## Milestone 1 Fit

| Requirement | Status | Notes |
|---|---|---|
| Observe-only: read miner status | **MET** | `read_status()` checks `observe` capability |
| Summary append to event spine | **MET** | `append_summary()` checks `summarize` capability |
| No direct miner control | **MET** | Double defense: adapter capability check + daemon header check |
| Event spine read: hermes_summary, miner_alert, control_receipt | **MET** | Whitelist filter in `get_filtered_events()` |
| Block user_message | **EXCEEDED** | Reference says read-only; impl blocks entirely (safer) |
| Authority token encodes principal, capabilities, expiration | **NOT MET** | Token is opaque UUID; capabilities stored server-side |
| Pairing endpoint | **MET** | `/hermes/pair` creates pairing with observe+summarize |
| CLI commands | **MET** | pair, connect, status, summary, events all functional |

The functional scope is achieved. The capability boundary is sound. The authentication model needs remediation (C1, C2) before the boundary is meaningful against a local adversary.

---

## Remaining Blockers

1. **C1 + C2 remediation** — Must fix before merge
2. **`tests/test_hermes.py`** — Not created. Boundary enforcement tests are needed to prevent regression of the capability scoping. The self-review acknowledges this.
3. **Smoke test update** — Not done

## Design Decisions to Record

1. **Lookup-based token vs encoded token:** The reference contract specifies an encoded token (principal + capabilities + expiration). The implementation chose a lookup-based UUID. This is a legitimate simplification for MVP but should be recorded as a design decision with rationale.

2. **user_message blocked vs read-only:** Implementation is more restrictive than the reference contract. Record as deliberate tightening with rationale (privacy-first posture).
