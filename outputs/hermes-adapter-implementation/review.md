# Hermes Adapter Implementation — Review

**Lane:** hermes-adapter-implementation
**Reviewed:** 2026-03-22
**Verdict:** CONDITIONAL PASS — functional core is sound; two blocking bugs fixed inline; security boundaries need hardening before milestone 2

## Summary

The adapter module (`hermes.py`) correctly implements the capability-scoped interface specified in the plan and `references/hermes-adapter.md`. The daemon endpoints follow the spec. The CLI subcommands were wired up but never dispatched (fixed inline). Core trust boundaries (capability checks, event filtering, expired token rejection) work as demonstrated by runtime verification.

## Files Touched

| File | Role | Lines Changed |
|------|------|---------------|
| `services/home-miner-daemon/hermes.py` | Adapter module (new) | +337 |
| `services/home-miner-daemon/daemon.py` | Daemon endpoints | +198/-16 |
| `services/home-miner-daemon/cli.py` | CLI hermes subcommands | +136/-0 |
| `outputs/hermes-adapter-implementation/spec.md` | Specification (new) | +308 |

## Inline Fixes Applied During Review

### Fix 1: CLI hermes dispatch missing (`cli.py:383`)

`main()` had no `elif args.command == 'hermes'` branch. All hermes CLI subcommands (`pair`, `connect`, `status`, `summary`, `events`) silently returned 0 with no effect. Added the dispatch block.

### Fix 2: CLI argparse mutual exclusion (`cli.py:342`)

`--token` was `required=True` alongside `--generate-token`. Passing `--generate-token` without `--token` would fail at argparse level. Changed `--token` to optional with a runtime check requiring one of the two.

## Pass 1 — First-Principles Challenge

### F1-CRITICAL: JWT signature not verified

**Location:** `hermes.py:47-77` (`_decode_jwt_payload`)

The adapter decodes the JWT payload (base64) but **never verifies the signature**. Any network client can forge a valid authority token by constructing `header.<base64_payload>.anything`. The token's self-declared `hermes_id`, `principal_id`, `capabilities`, and `exp` are trusted at face value.

**Impact:** The entire token validation flow is security theater. Anyone who can reach the daemon can impersonate any Hermes agent with any capabilities.

**Acceptable for milestone 1?** Yes, with caveats. The daemon binds to `127.0.0.1` (localhost only), and plan 006 (token auth) is listed as a dependency. The adapter is structurally ready for real signature verification — the `_decode_jwt_payload` function is the single point to harden. But this MUST be resolved before any LAN or network exposure.

**Recommendation:** Add a `# SECURITY: signature verification deferred to plan 006 (token auth)` comment at the call site, and block milestone 2 on it.

### F1-HIGH: No pairing verification in connect()

**Location:** `hermes.py:96-149`

`connect()` validates token structure but never checks whether the `hermes_id` has a valid pairing record via `get_hermes_pairing()`. The pairing store and connection store are completely decoupled. A Hermes agent can `connect()` without ever going through `pair_hermes()`.

**Impact:** The pairing ceremony is optional. Any valid-looking token connects regardless of pairing state.

**Recommendation:** Add `pairing = get_hermes_pairing(hermes_id)` check in `connect()`. Reject if no pairing exists.

### F1-HIGH: Unauthenticated `/hermes/pair` endpoint

**Location:** `daemon.py:305-322`

Anyone who can reach the daemon can pair a Hermes agent. No authentication or authorization required. Combined with the unsigned JWT, the full attack chain is: POST `/hermes/pair` → forge JWT → POST `/hermes/connect` → full observe+summarize access.

**Acceptable for milestone 1?** Marginally, given localhost-only binding. Same endpoint pattern as device pairing (`pair_client`), which is also unauthenticated. Both need auth gating in milestone 2.

## Pass 2 — Coupled-State Review

### F2-MEDIUM: Pairing store and connection store are decoupled

**Location:** `hermes.py:35` (in-memory dict) vs `store.py` (JSON file)

- Pairings persist to disk (`pairing-store.json`)
- Connections live in `_hermes_connections` (in-memory dict)
- Neither references the other

**Consequence:** After daemon restart, all Hermes connections are lost but pairings survive. A previously paired Hermes agent must reconnect, but nothing prevents connecting without pairing (see F1-HIGH above). If pairing is revoked by editing the store, existing connections remain active.

**Recommendation:** `connect()` should validate against the pairing store. `disconnect()` or a TTL sweep should be triggered when pairings are removed.

### F2-MEDIUM: `authority_scope` is unvalidated

**Location:** `hermes.py:206-236`, `daemon.py:330-331`

`append_summary()` accepts any string as `authority_scope`. A Hermes agent with `['observe', 'summarize']` capabilities can write events claiming `authority_scope: "control"`. Downstream consumers reading the spine would see misleading authority claims.

**Verified:** Runtime test confirmed `authority_scope: "control"` is accepted and persisted.

**Recommendation:** Validate `authority_scope` against `connection.capabilities` or `HERMES_CAPABILITIES`.

### F2-LOW: No input bounds on summary_text

**Location:** `hermes.py:206-236`, `daemon.py:330-333`

Empty strings and 100KB+ strings are accepted. The daemon endpoint checks `if not summary_text` but empty string `""` is falsy in Python — however this only catches `None`/missing, and the adapter layer has no check at all.

**Verified:** Runtime test confirmed empty string and 100KB payload both accepted at adapter level.

**Recommendation:** Add minimum length (>0 after strip) and maximum length (e.g., 10KB) validation in `append_summary()`.

## Pass 2 — Supplementary Checks

### Event filtering correctness: PASS

`get_filtered_events()` correctly filters to `HERMES_READABLE_EVENTS` (`hermes_summary`, `miner_alert`, `control_receipt`). `user_message` events are excluded. The over-fetch strategy (`limit * 2`) is adequate for milestone 1 spine volumes.

### Capability enforcement: PASS

Both `read_status()` and `append_summary()` check capabilities before executing. `get_filtered_events()` also checks `observe`. Capability checks use string membership against `connection.capabilities`, matching the plan.

### Control command blocking: PASS

`daemon.py:349-357` checks for `Hermes` auth header on control endpoints (`/miner/start`, `/miner/stop`, `/miner/set_mode`) and returns 403. This is defense-in-depth since Hermes connections lack control capability anyway.

### Idempotent pairing: PASS

`pair_hermes()` checks for existing pairing by `hermes_id` and returns the existing record. Re-pairing the same ID is safe.

### Spine append correctness: PASS

`append_summary()` delegates to `spine.append_event()` with `EventKind.HERMES_SUMMARY`, includes `hermes_id` in payload for attribution. Matches the spine contract.

## Pre-existing Issues (Not Introduced by This Lane)

### Enum serialization in `get_snapshot()`

`MinerStatus.STOPPED` serializes as `"MinerStatus.STOPPED"` (not `"stopped"`) on Python 3.15. Affects all status consumers including Hermes `read_status`. Pre-existing in `daemon.py`'s `MinerSimulator`. Should be fixed separately by using `.value` in `get_snapshot()`.

## Milestone Fit

| Plan Task | Status | Notes |
|-----------|--------|-------|
| Create hermes.py adapter module | DONE | |
| HermesConnection with authority token validation | DONE | Token structure validated; signature deferred to plan 006 |
| readStatus through adapter | DONE | |
| appendSummary through adapter | DONE | |
| Event filtering (block user_message) | DONE | |
| Hermes pairing endpoint | DONE | |
| CLI hermes subcommands | DONE | Fixed dispatch bug inline |
| Gateway client Agent tab | NOT STARTED | Plan milestone 3; not in this lane's scope |
| Tests | NOT STARTED | Plan milestone 4; no test file exists |

## Remaining Blockers

### Must-fix before lane closes:
1. **Connect must verify pairing** — `connect()` should reject unrecognized `hermes_id` (F1-HIGH)
2. **Validate authority_scope** — reject values outside `HERMES_CAPABILITIES` (F2-MEDIUM)

### Must-fix before milestone 2:
3. **JWT signature verification** — implement shared-secret HMAC or defer to plan 006 token auth (F1-CRITICAL)
4. **Authenticate `/hermes/pair`** — require gateway auth or principal proof (F1-HIGH)
5. **Fix enum serialization** — use `.value` in `get_snapshot()` return dict (pre-existing)

### Should-fix:
6. **Input bounds on summary_text** — min/max length validation
7. **Connection TTL or sweep** — expire idle connections
8. **Tests** — `test_hermes.py` per plan milestone 4

## Verdict

The adapter's architecture is correct. Capability scoping, event filtering, and the endpoint contract match the spec and reference contract. The two inline fixes (CLI dispatch, argparse conflict) unblock the CLI surface.

The security model is structurally present but not yet enforced end-to-end: unsigned JWTs and decoupled pairing/connection stores mean the trust boundary is porous. This is acceptable for milestone 1's localhost-only simulator posture, but the lane should not close without items 1-2 from the blockers list resolved.
