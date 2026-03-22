# Hermes Adapter Implementation — Honest Review

**Lane:** `hermes-adapter-implementation`
**Reviewed:** 2026-03-22
**Verdict:** CONDITIONAL PASS — functional core is sound; two blocking bugs were fixed inline during review; security boundaries need hardening before milestone 2

---

## Summary

The adapter module (`hermes.py`) correctly implements the capability-scoped interface. The daemon endpoints follow the spec. The CLI subcommands were wired up but never dispatched — fixed inline during review. Core trust boundaries (capability checks, event filtering, expired token rejection) work as demonstrated by runtime verification.

The security model is structurally present but not yet enforced end-to-end: unsigned JWTs and decoupled pairing/connection stores mean the trust boundary is porous. This is acceptable for milestone 1's localhost-only simulator posture, but two items must be resolved before this lane closes.

---

## Files Changed

| File | Role | Lines |
|------|------|-------|
| `services/home-miner-daemon/hermes.py` | Adapter module (new) | +337 |
| `services/home-miner-daemon/daemon.py` | Daemon endpoints | +198 / -16 |
| `services/home-miner-daemon/cli.py` | CLI hermes subcommands | +136 |
| `outputs/hermes-adapter-implementation/spec.md` | Specification (new) | +308 |

---

## Inline Fixes Applied During Review

### Fix 1: CLI hermes dispatch missing (`cli.py`)

`main()` had no `elif args.command == 'hermes'` branch. All five hermes subcommands (`connect`, `pair`, `status`, `summary`, `events`) silently returned 0 with no effect — they were parsed correctly but never dispatched.

**Fix:** Added the dispatch block inside the `elif args.command == 'hermes'` branch, routing each `hermes_command` value to its handler function.

### Fix 2: CLI argparse `--token` / `--generate-token` mutual exclusion (`cli.py`)

`--token` was `required=True` alongside `--generate-token` (action='store_true'). Passing `--generate-token` without `--token` failed at argparse level before reaching the handler.

**Fix:** Changed `--token` to optional, added a runtime guard in `cmd_hermes_connect` requiring exactly one of `--token` or `--generate-token`.

---

## Pass 1 — First-Principles Challenge

### F1-CRITICAL: JWT signature not verified

**Location:** `hermes.py` — `_decode_jwt_payload`

The adapter decodes the JWT payload (base64url) but **never verifies the signature**. Any client can forge a valid authority token by constructing `header.<base64_payload>.anything`. The token's self-declared `hermes_id`, `principal_id`, `capabilities`, and `exp` are trusted at face value.

**Impact:** Full attack chain — POST `/hermes/pair` → forge JWT with arbitrary hermes_id and all capabilities → POST `/hermes/connect` → complete observe+summarize access as any Hermes agent.

**Acceptable for milestone 1?** Yes, with caveat. The daemon binds to `127.0.0.1` only. The adapter is structurally ready for real signature verification — `_decode_jwt_payload` is the single injection point. **This MUST be resolved before milestone 2 (LAN exposure).**

**Recommendation:** Add a `# SECURITY: signature verification deferred to plan 006 (token auth)` comment at the call site. Block milestone 2 on it.

### F1-HIGH: No pairing verification in `connect()`

**Location:** `hermes.py` — `connect()`

`connect()` validates token structure but never checks whether `hermes_id` has a valid pairing record via `get_hermes_pairing()`. The pairing store (persistent JSON) and connection store (in-memory dict) are completely decoupled. A Hermes agent can `connect()` without ever calling `pair_hermes()`.

**Impact:** The pairing ceremony is optional. Any valid-looking token connects regardless of pairing state.

**Must fix before lane closes.**

**Recommendation:** Add `pairing = get_hermes_pairing(hermes_id)` check in `connect()`. Reject if `None`.

### F1-HIGH: Unauthenticated `/hermes/pair` endpoint

**Location:** `daemon.py` — `POST /hermes/pair`

Anyone who can reach the daemon can pair a Hermes agent. No authentication or authorization required. Combined with unsigned JWT (F1-CRITICAL), the full attack chain above applies.

**Acceptable for milestone 1?** Marginally, given localhost-only binding and the same pattern used by `pair_client`. Both need auth gating in milestone 2.

---

## Pass 2 — Coupled-State Review

### F2-MEDIUM: Pairing store and connection store are decoupled

**Location:** `hermes.py:35` (in-memory dict) vs `store.py` (JSON file)

- Pairings persist to `state/pairing-store.json`
- Connections live in `_hermes_connections` (in-memory dict)
- Neither store references the other

**Consequences:**
- After daemon restart, all Hermes connections are lost but pairings survive → previously paired Hermes must reconnect
- If a pairing is revoked by editing the store file, existing connections remain active (no revocation propagation)
- A valid-looking token connects even if the pairing was deleted

**Must fix before lane closes** (pairing verification in `connect()` addresses the most critical path).

### F2-MEDIUM: `authority_scope` is unvalidated

**Location:** `hermes.py` — `append_summary()`, `daemon.py` — `POST /hermes/summary`

`append_summary()` accepts any string as `authority_scope`. A Hermes agent with `['observe', 'summarize']` can write events claiming `authority_scope: "control"`. Downstream spine consumers see misleading authority claims.

**Verified by runtime test:** `authority_scope: "control"` is accepted and persisted.

**Should fix** (not blocking for milestone 1 since no downstream consumer exists yet). Validate `authority_scope in HERMES_CAPABILITIES`.

### F2-LOW: No input bounds on `summary_text`

**Location:** `hermes.py` — `append_summary()`, `daemon.py` — `POST /hermes/summary`

Empty strings and 100KB+ strings are accepted. The daemon endpoint checks `if not summary_text` but empty string `""` is falsy in Python — this catches `None`/missing but the adapter layer has no check.

**Verified by runtime test:** Empty string and 100KB payload both accepted at adapter level.

**Should fix:** Add minimum length (>0 after strip) and maximum length (e.g., 10KB) validation in `append_summary()`.

---

## Pass 2 — Supplementary Checks

### Event filtering correctness: PASS

`get_filtered_events()` filters to `HERMES_READABLE_EVENTS` (`hermes_summary`, `miner_alert`, `control_receipt`). `user_message` events are excluded. The over-fetch strategy (`limit * 2`) is adequate for milestone 1 spine volumes.

### Capability enforcement: PASS

`read_status()` and `append_summary()` both check capabilities before executing. `get_filtered_events()` also checks `observe`. Capability checks use string membership against `connection.capabilities`, matching the plan.

### Control command blocking: PASS

`daemon.py` checks for `Hermes` auth header on control endpoints (`/miner/start`, `/miner/stop`, `/miner/set_mode`) and returns 403. Defense-in-depth; Hermes connections lack `control` capability so the adapter would reject first anyway.

### Idempotent pairing: PASS

`pair_hermes()` checks for existing pairing by `hermes_id` and returns the existing record. Re-pairing the same ID is safe.

### Spine append correctness: PASS

`append_summary()` delegates to `spine.append_event()` with `EventKind.HERMES_SUMMARY`, includes `hermes_id` in payload for attribution. Matches the spine contract.

---

## Pre-existing Issues (Not Introduced by This Lane)

### Enum serialization in `get_snapshot()`

`MinerStatus.STOPPED` serializes as `"MinerStatus.STOPPED"` (Python repr) instead of `"stopped"` on Python 3.15. Affects all status consumers including Hermes `read_status`. Pre-existing in `MinerSimulator.get_snapshot()`.

**Fix:** Use `.value` when constructing the return dict in `get_snapshot()`.

---

## Milestone Fit

| Plan Task | Status | Notes |
|-----------|--------|-------|
| Create `hermes.py` adapter module | DONE | |
| HermesConnection with authority token validation | DONE | Token structure validated; signature deferred to plan 006 |
| `readStatus` through adapter | DONE | |
| `appendSummary` through adapter | DONE | |
| Event filtering (block user_message) | DONE | |
| Hermes pairing endpoint | DONE | |
| CLI hermes subcommands | DONE | Fixed dispatch bug inline |
| Gateway client Agent tab | NOT STARTED | Plan milestone 3; not in this lane's scope |
| Tests | NOT STARTED | Plan milestone 4; no test file exists |

---

## Remaining Blockers

### Must fix before lane closes

1. **Connect must verify pairing** — `connect()` should reject unrecognized `hermes_id` (F1-HIGH)
2. **Validate `authority_scope`** — reject values outside `HERMES_CAPABILITIES` (F2-MEDIUM)

### Must fix before milestone 2

3. **JWT signature verification** — implement shared-secret HMAC or defer to plan 006 (F1-CRITICAL)
4. **Authenticate `/hermes/pair`** — require gateway auth or principal proof (F1-HIGH)
5. **Fix enum serialization** — use `.value` in `get_snapshot()` return dict (pre-existing)

### Should fix

6. **Input bounds on `summary_text`** — min/max length validation in `append_summary()`
7. **Connection TTL or sweep** — expire idle connections after daemon restart
8. **Revocation propagation** — disconnect Hermes when its pairing is removed
9. **Tests** — `test_hermes.py` per plan milestone 4

---

## Verdict

The adapter's architecture is correct. Capability scoping, event filtering, and the endpoint contract match the spec and reference contract. The two inline fixes (CLI dispatch, argparse conflict) unblock the CLI surface.

The security model is structurally present but not yet enforced end-to-end. This is acceptable for milestone 1's localhost-only simulator posture, but the lane should not close without items 1–2 from the blockers list resolved.

**Lane status: CONDITIONAL PASS — close after F1-HIGH and F2-MEDIUM fixes.**
