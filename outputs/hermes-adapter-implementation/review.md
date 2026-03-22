# Hermes Adapter Implementation — Review

**Lane:** hermes-adapter-implementation
**Plan:** genesis/plans/009-hermes-adapter-implementation.md
**Reviewer:** Claude Opus 4.6 (Nemesis-style security review)
**Date:** 2026-03-22
**Verdict:** PASS WITH FIXES APPLIED

## Review Summary

The Hermes adapter implementation is architecturally sound and feature-complete for Milestone 1. Four bugs were found and fixed during review. After fixes, all 11 tests pass and the CLI works correctly.

## Bugs Found and Fixed

### BUG-1: test_hermes.py — Undefined class reference (BLOCKER)

**File:** `services/home-miner-daemon/tests/test_hermes.py:148`
**Severity:** Blocker — tests cannot run
**Issue:** `TestDaemon()` referenced but only `HermesTestDaemon` is defined.
**Fix:** Changed `TestDaemon()` to `HermesTestDaemon()`.

### BUG-2: daemon.py — Auth error returns falsy sentinel (FUNCTIONAL)

**File:** `services/home-miner-daemon/daemon.py:177-212`
**Severity:** High — auth rejection double-faults
**Issue:** `_require_hermes_auth()` returns `(None, self._send_json(...))`. Since `_send_json` returns `None`, the caller gets `(None, None)`. The `if err:` guard evaluates to `False`, and the handler proceeds with `conn=None`, crashing with `AttributeError`. The 401 headers are already on the wire, so the client sees a mangled response.
**Fix:** Call `_send_json` first, then `return None, True` to make the error sentinel truthy.

### BUG-3: cli.py — Function shadowing and missing main() (BLOCKER)

**File:** `services/home-miner-daemon/cli.py:327-420`
**Severity:** Blocker — CLI completely broken
**Issue:** The argparse setup and dispatch logic at line 327 was defined as `def daemon_call(...)`, shadowing the real HTTP caller at line 28. Every `cmd_*` function that calls `daemon_call('GET', '/status')` would invoke the parser setup instead. Additionally, `main()` was called at line 420 but never defined. The local variable `hermes` (the argparse subparser) shadowed the `hermes` module import.
**Fix:** Renamed the second `daemon_call` to `main()`. Renamed the argparse local variable from `hermes` to `hermes_cmd` to avoid shadowing the module import.

### BUG-4: hermes.py — Missing principal_id cross-validation (SECURITY)

**File:** `services/home-miner-daemon/hermes.py:299-302`
**Severity:** Medium — privilege escalation via forged token
**Issue:** After finding a pairing record by hermes_id, the code did not verify that the token's `principal_id` matches the pairing record's `principal_id`. An attacker who knows a valid hermes_id could forge a token with a different principal_id and connect under that principal's identity.
**Fix:** Added cross-validation: `if pairing_record['principal_id'] != token.principal_id: raise ValueError("PAIRING_PRINCIPAL_MISMATCH")`.

## Nemesis Security Review

### Pass 1 — First-Principles Challenge

#### Trust Boundaries

| Boundary | Enforced | Evidence |
|----------|----------|---------|
| Hermes cannot control miner | YES | daemon.py rejects `Authorization: Hermes` on POST /miner/* with 403 |
| Hermes cannot read user_message | YES | hermes.py `get_filtered_events` whitelist excludes user_message |
| Hermes cannot claim 'control' capability | YES | `_validate_hermes_capabilities` rejects unknown capabilities |
| Expired tokens rejected | YES | `_is_token_expired` + server-side pairing expiration check |
| Token principal must match pairing | YES (after fix) | Added in BUG-4 fix |

#### Authority Assumptions

The token is a self-describing JSON blob — not cryptographically signed. In M1 (LAN-only, simulator), this is acceptable because the threat model is "honest Hermes agent, prevent accidental overreach." In production, the token must be signed or replaced with a proper credential.

#### Who Can Trigger Dangerous Actions

- **Pairing:** Anyone on the LAN can call POST /hermes/pair (no auth required). Acceptable for M1 LAN-only. Must be gated before network exposure.
- **Summary append:** Requires valid, unexpired token with 'summarize' capability. Correct.
- **Status read:** Requires valid, unexpired token with 'observe' capability. Correct.
- **Control:** Blocked for all Hermes tokens regardless of content. Correct.

### Pass 2 — Coupled-State Review

#### Paired State: Pairing Store vs Token

The pairing record in `hermes-pairing-store.json` and the authority token issued to Hermes encode overlapping state (principal_id, capabilities, expiration). These can drift:

- **Re-pairing refreshes** the store's `token_expires_at` but does not invalidate outstanding tokens. An old token remains valid until its own expiration. This is acceptable for M1 — tokens are short-lived (30 days) and LAN-only.
- **Capability narrowing** is not supported. If the store record's capabilities were modified, old tokens would still carry the original capabilities. The adapter validates capabilities against the HERMES_CAPABILITIES whitelist (not the store record), so this cannot escalate — but it means capability revocation requires token expiration or a version bump.

#### Event Spine Consistency

- `append_hermes_summary` is append-only and idempotent (each call creates a new event with a unique UUID). No consistency concerns.
- `get_filtered_events` over-fetches by 3x and filters. If the spine grows large, this is inefficient but correct.

#### Idempotence

- Pairing: Idempotent by hermes_id. Re-pairing updates expiration, does not duplicate.
- Summary append: Not idempotent (each call creates a new event). This is correct — summaries are distinct events.
- Connect: Stateless validation, idempotent.

### State Transitions

| Transition | Mutates | Safe |
|-----------|---------|------|
| pair_hermes | hermes-pairing-store.json, event spine | YES — append-only store, idempotent re-pair |
| connect | _hermes_connections dict (in-memory) | YES — overwrite is idempotent |
| append_summary | event-spine.jsonl | YES — append-only |
| get_filtered_events | nothing | YES — read-only |
| read_status | nothing | YES — read-only |

### Secret Handling

- Authority tokens are transmitted in HTTP headers (`Authorization: Hermes <token>`). Over LAN HTTP in M1, this is acceptable. Must move to HTTPS before network exposure.
- Tokens are not logged or echoed in error responses. Correct.
- Token contents are not persisted server-side (only the pairing record is stored). Correct.

### Failure Modes

- **Daemon crash during summary append:** JSONL write is atomic per line (single `f.write` call). Partial writes are possible but unlikely. A production spine should use fsync or WAL.
- **Concurrent pairing:** `load_hermes_pairings()` / `save_hermes_pairings()` is not locked. Two concurrent pair requests could lose one write. Acceptable for M1 (single-user, LAN-only).

## Milestone Fit

### Plan Tasks — Status After Review

| Task | Status | Evidence |
|------|--------|---------|
| Create hermes.py adapter module | DONE | hermes.py: 468 lines, all adapter functions implemented |
| HermesConnection with authority token validation | DONE | connect() validates version, expiration, capabilities, pairing, principal_id |
| readStatus through adapter | DONE | read_status() delegates to miner.get_snapshot() with observe check |
| appendSummary through adapter | DONE | append_summary() writes to spine with summarize check |
| Event filtering (block user_message) | DONE | get_filtered_events() whitelist excludes user_message |
| Hermes pairing endpoint | DONE | POST /hermes/pair in daemon.py |
| Update CLI with Hermes subcommands | DONE | cli.py hermes pair/status/summary/events (fixed during review) |
| Tests for adapter boundary enforcement | DONE | 11 tests, all passing |
| Update gateway client Agent tab | NOT STARTED | Correctly scoped out of this lane (Milestone 3) |

### Remaining Blockers

None. All blocking bugs have been fixed. The lane is unblocked.

### Observations for Future Work

1. **Pairing endpoint returns no token** — The HTTP `POST /hermes/pair` endpoint returns the pairing record but not the authority token. The CLI builds one from the pairing record. A non-CLI consumer (e.g., a real Hermes agent connecting over HTTP) would need the token returned from the pair endpoint. This is an M2 concern.

2. **Reference spec ambiguity** — `references/hermes-adapter.md` line 74 lists "Read-only access to user messages" under Milestone 1 boundaries. The Event Spine Access section (lines 59-65) does NOT include user_message in Hermes-readable events. The implementation correctly follows the Event Spine Access section (user_message filtered out). The boundary section should be clarified to read "No access to user messages" to match the implementation.

3. **Token is not cryptographically signed** — Acceptable for M1 LAN-only. Must be addressed before any network exposure.

4. **Smoke script uses direct spine access** — `scripts/hermes_summary_smoke.sh` calls `spine.append_hermes_summary` directly rather than going through the adapter. It should be updated to use the HTTP endpoints once the adapter is live.

## Test Results

```
tests/test_hermes.py::TestHermesAdapter::test_hermes_append_summary PASSED
tests/test_hermes.py::TestHermesAdapter::test_hermes_connect_expired PASSED
tests/test_hermes.py::TestHermesAdapter::test_hermes_connect_valid PASSED
tests/test_hermes.py::TestHermesAdapter::test_hermes_event_filter PASSED
tests/test_hermes.py::TestHermesAdapter::test_hermes_idempotent_pairing PASSED
tests/test_hermes.py::TestHermesAdapter::test_hermes_invalid_capability PASSED
tests/test_hermes.py::TestHermesAdapter::test_hermes_no_control PASSED
tests/test_hermes.py::TestHermesAdapter::test_hermes_pair PASSED
tests/test_hermes.py::TestHermesAdapter::test_hermes_read_status PASSED
tests/test_hermes.py::TestHermesAdapter::test_hermes_summary_appears_in_events PASSED
tests/test_hermes.py::TestHermesAdapter::test_hermes_unauthorized_status PASSED

11 passed in 0.77s
```

## Verdict

**PASS.** The Hermes adapter implementation is correct, secure within its M1 threat model, and complete for the scoped milestones. Four bugs were found and fixed during this review. The lane is unblocked.
