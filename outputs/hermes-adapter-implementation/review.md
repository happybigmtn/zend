# Hermes Adapter — Honest Review

**Reviewer:** Nemesis security review  
**Model:** Claude Opus 4.6  
**Date:** 2026-03-22  
**Slice:** hermes-adapter-implementation  
**Status:** CONDITIONAL APPROVE

---

## Executive Summary

The Hermes adapter module (`hermes.py`) correctly enforces its stated capability boundary: `observe` + `summarize` only, `user_message` filtered, and control capability rejected at token validation. All 19 unit tests pass. Two bugs were caught and fixed during review.

The capability boundary is architecturally sound at the adapter layer. The residual risk is that the daemon the adapter sits in front of has no HTTP-level auth on `/miner/*` endpoints. This is a pre-existing condition, not introduced by this slice, but it means the "Hermes cannot control the miner" invariant only holds at the adapter API level — not at the raw HTTP layer.

---

## Compliance Checklist

| # | Requirement | Verdict | Evidence |
|---|-------------|---------|----------|
| 1 | Hermes can connect with valid authority token | PASS | `test_hermes_connect_valid` |
| 2 | Hermes can read miner status | PASS | `test_hermes_read_status` |
| 3 | Hermes can append summaries to spine | PASS | `test_hermes_append_summary` |
| 4 | Hermes adapter rejects control capability | PASS | `test_hermes_invalid_capability_rejected` |
| 5 | Hermes cannot read user_message events | PASS | `test_hermes_event_filter` |
| 6 | Expired tokens are rejected | PASS | `test_hermes_connect_expired` |
| 7 | Invalid capabilities rejected at pairing time | PASS | `test_pair_hermes_invalid_capability` |
| 8 | CLI exposes Hermes subcommands | PASS | `hermes pair`, `status`, `summary`, `events`, `list` |
| 9 | All 19 tests pass | PASS | `pytest -v` — 0.04s wall time |
| 10 | Miner control endpoints enforce auth | **FAIL** | S-1 below (pre-existing) |

---

## Security Findings

### S-1 [HIGH] — `/miner/*` endpoints have no authentication

**File:** `services/home-miner-daemon/daemon.py` lines 259–271

`POST /miner/start`, `/miner/stop`, and `/miner/set_mode` execute without checking any auth header. The Hermes `Authorization` header is only processed on paths that start with `/hermes/`. Any LAN client — including a Hermes-identified one — can start or stop the miner by calling these paths directly.

This is a pre-existing daemon condition. The prior auto-review incorrectly stated "Control endpoints require gateway auth." That claim is corrected here. The adapter's capability restriction is real and enforced within its own API surface, but it does not gate the underlying `/miner/*` paths because those paths are not part of the adapter's surface — they are part of the daemon's root HTTP interface.

**Why it matters:** If the daemon is exposed beyond the local machine (e.g., misconfigured LAN binding), an attacker with knowledge of a valid `hermes_id` could control the miner without any capability check.

**Scope:** Pre-existing. Plan 006 (daemon token auth) must gate `/miner/*` before the "Hermes cannot control" invariant holds at the HTTP layer.

---

### S-2 [MEDIUM] — Authority tokens are forgeable unsigned JSON

**File:** `services/home-miner-daemon/hermes.py` lines 113–164

`connect()` parses a JSON authority token and validates structure, capabilities, and expiration — but does not verify the token was issued by the daemon. Anyone who knows a valid `principal_id` (returned in the pairing response) can construct a token that passes validation.

**Current mitigation:** The HTTP endpoints use `validate_hermes_auth()`, which authenticates against the persistent pairing store using the `Authorization: Hermes <id>` header. Token forgery alone does not grant HTTP access — the pairing must also exist in `hermes-pairing.json`. The `connect()` path is used only for reconnection and its result is not persisted.

**Residual risk:** If future code paths use `connect()` to establish sessions without a pairing existence check, forgery becomes exploitable. Token format should gain HMAC signatures when Plan 006 lands.

---

### S-3 [MEDIUM] — `/hermes/pair` is unauthenticated

**File:** `services/home-miner-daemon/daemon.py` lines 277–303

`POST /hermes/pair` creates a Hermes pairing and returns an authority token without any authentication. Any LAN client can self-pair as a Hermes agent.

**Scope:** Acceptable for M1 LAN-only deployment. Gateway device pairing has the same model. Must be gated before any network-exposed deployment.

---

### S-4 [LOW] — No length validation on summary payload

**File:** `services/home-miner-daemon/hermes.py` lines 302–333, `daemon.py` lines 337–355

`summary_text` (free text) and `authority_scope` (free string) have no length or format limits. A Hermes agent with `summarize` capability could write arbitrarily large summaries or use confusing `authority_scope` values.

**Recommendation:** Cap `summary_text` at a reasonable size (e.g., 10 KB) and validate `authority_scope` against a known enum or allowlist.

---

### S-5 [LOW] — Non-atomic read-modify-write on Hermes pairing store

**File:** `services/home-miner-daemon/hermes.py` `_get_hermes_pairings`, `_save_hermes_pairings`

Read-modify-write on `state/hermes-pairing.json` is not atomic. Concurrent HTTP requests handled by `ThreadedHTTPServer` could lose writes.

**Scope:** Acceptable for M1 single-user context. Address with file locking or a WAL if Hermes pairings become concurrent.

---

### S-6 [INFO] — Redundant comparison in `validate_hermes_auth`

**File:** `services/home-miner-daemon/hermes.py` lines 395–397

```python
def validate_hermes_auth(hermes_id: str, auth_header: str) -> Optional[HermesConnection]:
    ...
    if header_hermes_id != hermes_id:   # ← always False when called correctly
        return None
```

The caller in `daemon.py` extracts `hermes_id` from the header and passes it as both the `hermes_id` parameter and as the ID embedded in `auth_header`. The comparison at line 396 is therefore a no-op. Not a security bug — the function signature implies a cross-check that doesn't happen, but the pairing existence check at line 399 is what actually gates access.

---

## Bugs Fixed During Review

### B-1 — CLI `--capabilities` passed as raw string instead of list

**File:** `services/home-miner-daemon/cli.py` line 216

`cmd_hermes_pair` passed `args.capabilities` (a string like `"observe,summarize"`) directly to `pair_hermes()`, which expects `Optional[List[str]]`. Iterating a string yields individual characters, which then fail the allowlist check. The default `None` path worked, masking the bug for all tests that used defaults.

**Fix:** Added `.split(',')` to match the pattern already used in `cmd_pair` (line 112).

### B-2 — Inconsistent `STATE_DIR` calculation in `hermes.py`

**File:** `services/home-miner-daemon/hermes.py` `_get_hermes_pairings`, `_save_hermes_pairings`

The pairing file path used `os.path.join(os.path.dirname(__file__), '..', '..')` without `.resolve()`, re-evaluating `ZEND_STATE_DIR` on every call. All other daemon modules (`spine.py`, `store.py`, `daemon.py`) use module-level `Path(__file__).resolve().parents[2]` cached in a `STATE_DIR` constant.

**Fix:** Added module-level `STATE_DIR` and `HERMES_PAIRING_FILE` constants matching the codebase convention.

---

## Adapter Boundary Assessment

### What the adapter correctly enforces

| Boundary | Mechanism | Tested |
|----------|-----------|--------|
| Capability allowlist | `HERMES_CAPABILITIES = ['observe', 'summarize']` | Yes — 4 dedicated tests |
| `observe` required for `read_status` | `PermissionError` check | Yes |
| `summarize` required for `append_summary` | `PermissionError` check | Yes |
| `user_message` filtered from event reads | Allowlist-based `HERMES_READABLE_EVENTS` | Yes |
| Token expiration enforcement | `_is_token_expired()` check | Yes |
| Pairing capability validation | Rejects caps outside allowlist | Yes |

### What the adapter does NOT enforce (requires daemon/gateway layer)

| Gap | Current state | Required for |
|-----|---------------|--------------|
| `/miner/*` endpoint auth | None (S-1) | Plan 006 |
| `/hermes/pair` endpoint auth | None (S-3) | Network-exposed deployment |
| Token provenance verification | Unsigned JSON (S-2) | Plan 006 |

---

## Test Coverage Assessment

19 tests provide thorough module-level coverage. The following gaps exist:

- **No HTTP-level integration tests.** Tests run against in-process `HermesConnection` objects without exercising the daemon HTTP interface.
- **No CLI `--capabilities` parsing test.** B-1 was masked because all CLI tests used the default capability path.
- **No test for Hermes-authenticated `/miner/start` rejection.** The current code does not reject these — it never reaches them through the Hermes API surface (S-1).

---

## Milestone Fit

The adapter delivers what the plan specifies for Milestone 1:
- Python module scoping Hermes to `observe` + `summarize`
- `user_message` events filtered from Hermes reads
- Daemon HTTP endpoints for pairing, reconnect, status, summary, and events
- CLI subcommands for all operations
- 19 passing unit tests

The Agent tab update and end-to-end smoke test are deferred per the plan.

---

## Verdict

**CONDITIONAL APPROVE.** The capability boundary is architecturally correct. The adapter correctly enforces `observe` + `summarize` scoping and filters `user_message` events. The daemon-level HTTP auth gap (S-1) is pre-existing and outside this slice's scope, but it must be resolved by Plan 006 before "Hermes cannot control" holds at the HTTP layer.

---

## Sign-off

| Role | Name | Date |
|------|------|------|
| Implementer | Specify agent (MiniMax-M2.7) | 2026-03-22 |
| Nemesis reviewer | Opus 4.6 | 2026-03-22 |
| Polish reviewer | Opus 4 | 2026-03-22 |
