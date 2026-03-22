# Hermes Adapter Implementation — Review

**Reviewer:** Nemesis security review (Opus 4.6)
**Date:** 2026-03-22
**Status:** CONDITIONAL APPROVE — adapter boundary is sound; daemon auth gap documented below

## Executive Summary

The Hermes adapter module (`hermes.py`) correctly enforces its capability boundary: observe+summarize only, user_message filtered, control capability rejected at token validation. 19 unit tests pass. Two bugs were found and fixed during review.

However, the prior auto-review contained a false claim: "Control endpoints require gateway auth, not Hermes auth." In reality, `/miner/start`, `/miner/stop`, `/miner/set_mode` have **zero authentication**. Any LAN client — Hermes-identified or otherwise — can call them. This is a pre-existing daemon condition, not introduced by this slice, but the review must not claim a protection that does not exist.

## Compliance Checklist

| # | Requirement | Verdict | Evidence |
|---|-------------|---------|----------|
| 1 | Hermes can connect with authority token | PASS | `test_hermes_connect_valid` |
| 2 | Hermes can read miner status | PASS | `test_hermes_read_status` |
| 3 | Hermes can append summaries to spine | PASS | `test_hermes_append_summary` |
| 4 | Hermes adapter rejects control capability | PASS | `test_hermes_invalid_capability_rejected` |
| 5 | Hermes cannot read user_message events | PASS | `test_hermes_event_filter` |
| 6 | Expired tokens rejected | PASS | `test_hermes_connect_expired` |
| 7 | Invalid capabilities rejected at pairing | PASS | `test_pair_hermes_invalid_capability` |
| 8 | CLI provides Hermes subcommands | PASS | pair, status, summary, events, list |
| 9 | All 19 tests pass | PASS | `pytest -v` verified during review (0.04s) |
| 10 | Miner control endpoints enforce auth | **FAIL** | See S-1 below. Pre-existing, not introduced here. |

## Nemesis Security Findings

### S-1 [HIGH] — Miner control endpoints have no authentication (pre-existing)

**Location:** `daemon.py:259-271`

`POST /miner/start`, `/miner/stop`, `/miner/set_mode` execute unconditionally. The Hermes `Authorization` header is ignored on non-`/hermes/` paths. A Hermes client — or any LAN client — can start/stop the miner by hitting these paths directly.

**Why this matters:** The adapter's capability restriction is only meaningful if the underlying endpoints it protects are otherwise gated. Without daemon-level auth, the adapter is a locked door next to an open window.

**Scope:** This is a pre-existing daemon condition, not introduced by the Hermes slice. The prior auto-review falsely claimed "Control endpoints require gateway auth" — corrected here.

**Recommendation:** Plan 006 (token auth) should gate `/miner/*` endpoints before Hermes boundary claims become meaningful at the HTTP layer.

### S-2 [MEDIUM] — Authority tokens are unsigned JSON, forgeable by any principal_id holder

**Location:** `hermes.py:113-164`

`connect()` parses a JSON string and validates structure, capabilities, and expiration — but does not verify the token was issued by the daemon. Any entity that knows a valid `principal_id` (returned in pairing responses) can forge tokens.

**Mitigation (current):** The HTTP endpoints use `validate_hermes_auth()` which authenticates against the pairing store via the `Authorization: Hermes <id>` header. The `connect()` token path is only used for reconnection and its result is not stored. So token forgery alone does not grant HTTP access — the pairing must exist.

**Residual risk:** If future code paths use `connect()` to establish sessions without a pairing check, forgery becomes exploitable. The token format should gain HMAC signatures when plan 006 lands.

### S-3 [MEDIUM] — Pairing endpoint is unauthenticated

**Location:** `daemon.py:277-303`

`POST /hermes/pair` creates a Hermes pairing and returns an authority token with no authentication. Any LAN client can self-pair as a Hermes agent.

**Scope:** Acceptable for M1 LAN-only (gateway device pairing has the same model). Must be gated before any network-exposed deployment.

### S-4 [LOW] — No input validation on summary payload

**Location:** `hermes.py:302-333`, `daemon.py:337-355`

`summary_text` and `authority_scope` are free-text strings with no length limits or validation. Disk-fill via large summaries, or confusing `authority_scope` values, are possible.

**Recommendation:** Add a reasonable length cap (e.g. 10KB) and validate `authority_scope` against a known enum.

### S-5 [LOW] — File I/O race condition on Hermes pairing store

**Location:** `hermes.py:_get_hermes_pairings`, `_save_hermes_pairings`

Read-modify-write on `hermes-pairing.json` is not atomic. Concurrent HTTP requests via `ThreadedHTTPServer` could lose writes. Acceptable for M1 single-user context.

### S-6 [INFO] — `validate_hermes_auth` redundant ID comparison

**Location:** `hermes.py:395-397`

The caller in `daemon.py` extracts `hermes_id` from the header and passes it as both the `hermes_id` parameter and inside `auth_header`. The comparison at line 396 (`header_hermes_id != hermes_id`) is therefore always a no-op. Not a bug, but the function signature implies a cross-check that doesn't actually happen.

## Bugs Fixed During Review

### B-1 — CLI `--capabilities` passed as raw string (fixed)

**Location:** `cli.py:216`

`cmd_hermes_pair` passed `args.capabilities` (a string like `"observe,summarize"`) directly to `pair_hermes()`, which expects `Optional[List[str]]`. Iterating a string yields characters, failing the allowlist check. The default `None` path worked, masking the bug.

**Fix:** Added `.split(',')` to match the pattern used in `cmd_pair` (line 112).

### B-2 — `hermes.py` state_dir calculated inconsistently (fixed)

**Location:** `hermes.py:_get_hermes_pairings`, `_save_hermes_pairings`

Used `os.path.join(os.path.dirname(__file__), '..', '..')` without `.resolve()`, re-read `ZEND_STATE_DIR` on every call. All other modules (`spine.py`, `store.py`, `daemon.py`) use module-level `Path(__file__).resolve().parents[2]` cached in `STATE_DIR`.

**Fix:** Added module-level `STATE_DIR` and `HERMES_PAIRING_FILE` constants matching codebase convention.

## Adapter Boundary Analysis

### What the adapter correctly enforces (at the Python module level)

| Boundary | Mechanism | Tested |
|----------|-----------|--------|
| Capability allowlist | `HERMES_CAPABILITIES = ['observe', 'summarize']` | Yes (4 tests) |
| observe required for read_status | `PermissionError` check | Yes |
| summarize required for append_summary | `PermissionError` check | Yes |
| user_message event filtering | Allowlist-based (`HERMES_READABLE_EVENTS`) | Yes |
| Token expiration | `_is_token_expired()` check | Yes |
| Pairing capability validation | Rejects caps outside allowlist | Yes |

### What the adapter does NOT enforce (requires daemon/gateway auth)

| Gap | Current state | Required for |
|-----|---------------|--------------|
| Miner control endpoint auth | No auth (S-1) | Plan 006 |
| Pairing endpoint auth | No auth (S-3) | Network deployment |
| Token provenance verification | Unsigned JSON (S-2) | Plan 006 |

## Test Coverage Assessment

19 tests cover the adapter module thoroughly. Missing coverage:

- No HTTP-level integration tests (daemon must be running)
- No test for CLI `--capabilities` parsing (B-1 was missed because tests only exercise default capabilities)
- No test verifying that Hermes-authenticated requests to `/miner/start` are rejected (they aren't — S-1)

## Milestone Fit

The adapter delivers what plan 009 Milestone 1 specifies: a Python module that scopes Hermes to observe+summarize, filters user_message events, and provides daemon endpoints and CLI for testing. The Agent tab update and smoke test are deferred per plan.

The boundary is architecturally correct. The gap is that the daemon it sits in front of has no auth layer yet. This slice cannot fix that — plan 006 must land first for the boundary to hold end-to-end.

## Remaining Blockers

| Blocker | Severity | Blocks |
|---------|----------|--------|
| Daemon auth on `/miner/*` (S-1) | HIGH | Truthful "Hermes cannot control" claim at HTTP level |
| Token signing (S-2) | MEDIUM | Token-based reconnection security |
| Agent tab update | LOW | UX completeness (plan says later) |

## Verdict

**CONDITIONAL APPROVE.** The Hermes adapter module is correctly implemented, well-tested, and fits the milestone. The capability boundary is sound at the adapter level. The daemon-level auth gap (S-1) is pre-existing and outside this slice's scope, but must be resolved by plan 006 before the "Hermes cannot control" invariant holds end-to-end.

### Sign-off

| Role | Name | Date |
|------|------|------|
| Implementer | Specify agent (MiniMax-M2.7) | 2026-03-22 |
| Nemesis reviewer | Opus 4.6 | 2026-03-22 |
