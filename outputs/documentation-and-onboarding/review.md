# Documentation & Onboarding — Review

**Lane:** documentation-and-onboarding
**Reviewed:** 2026-03-22
**Verdict:** BLOCKED — plan must be corrected before implementation can begin

## Executive Summary

The specify stage was a no-op (MiniMax-M2.7-highspeed, 0 tokens in / 0 tokens out). No spec artifact was produced by the prior stage. The plan exists and is structurally sound as an ExecPlan, but contains 7 factual errors against the current codebase that would cause the resulting documentation to be wrong on first write. None of the 6 progress items have been started.

This lane is documentation-only (no code changes), so the security surface is the *accuracy* of what gets documented. Inaccurate docs are worse than no docs — they create false confidence in operators and contributors.

## Correctness Audit

### Factual Errors in Plan (must fix before implementation)

| # | Claim in Plan | Reality | Severity |
|---|---------------|---------|----------|
| 1 | Endpoint `GET /spine/events` exists | Not implemented. Events are CLI-only via `cli.py events` | **High** — API reference would document a 404 |
| 2 | Endpoint `GET /metrics` exists | Not implemented | **High** — same |
| 3 | Endpoint `POST /pairing/refresh` exists | Not implemented (noted "from plan 006" but plan 006 hasn't landed) | **High** — same |
| 4 | Health returns `{"status": "ok"}` | Returns `{"healthy": true, "temperature": 45.0, "uptime_seconds": 0}` | **Medium** — quickstart proof is wrong |
| 5 | Env var `ZEND_TOKEN_TTL_HOURS` exists | Not in code. `ZEND_DAEMON_URL` exists but is omitted | **Medium** — operator guide would reference phantom config |
| 6 | `python3 -m pytest services/home-miner-daemon/ -v` runs tests | Zero test files exist in the repo | **Medium** — README would claim testability that doesn't exist |
| 7 | Quickstart: `bootstrap` then `control --action set_mode` | Bootstrap grants only `observe`. Control requires `control` capability. Sequence fails with "unauthorized" | **High** — the 5-command quickstart is broken |

### Path Reference Errors

The plan references files that do not exist in the repo tree:
- `genesis/plans/008-documentation-and-onboarding.md` — no `genesis/` directory exists
- `genesis/plans/001-master-plan.md` — same
- `genesis/SPEC.md` — same

These are fabro orchestration references, not repo-level files. The plan should reference `plans/`, `specs/`, and `references/` which do exist.

## Milestone Fit

| Milestone | Assessment |
|-----------|------------|
| M1: README Rewrite | Achievable after fixing quickstart sequence and health response |
| M2: Contributor Guide | Achievable, but must acknowledge no tests exist yet |
| M3: Operator Quickstart | Achievable after removing phantom env var, fixing auth description |
| M4: API Reference | Achievable only after reducing endpoint list from 8 to 5 |
| M5: Architecture Doc | Achievable — codebase is small and well-structured |

The milestones are correctly scoped and ordered. The work is straightforward documentation once the plan's factual errors are corrected.

## Remaining Blockers

1. **Plan correction** — the 7 factual errors above must be fixed in the plan before any documentation is written
2. **Auth gap documentation decision** — the plan must decide whether to document the HTTP layer as unauthenticated (truthful) or to claim capability-scoped auth (misleading). The honest answer: HTTP endpoints are open to any LAN client; capability checks exist only in the CLI wrapper
3. **Test story** — README should either omit pytest or note that tests are a future addition

## Nemesis Pass 1 — First-Principles Trust Boundary Challenge

This lane produces documentation, not code. The trust boundary question is: *does the documentation accurately represent the security posture, or does it create false assurance?*

### Finding N1.1: Documentation would overstate auth enforcement

The plan's Milestone 4 says endpoints have "Authentication requirement (none, observe, control)". In reality, ALL HTTP endpoints are unauthenticated. The `observe`/`control` capability system exists only in `cli.py`, not in `daemon.py`'s HTTP handlers. A direct `curl POST http://<host>:8080/miner/start` succeeds from any machine on the LAN.

**Risk:** An operator reading the API reference would believe the daemon enforces capability-scoped access at the HTTP layer. It does not. Any device on the LAN can control the miner.

**Recommendation:** The API reference must clearly state: "Milestone 1 HTTP endpoints are unauthenticated. Capability enforcement exists only in the CLI layer. Do not expose the daemon port beyond the local network."

### Finding N1.2: Token expiration is a dead placeholder

`store.py:88-89` creates pairing tokens with `expires = datetime.now(timezone.utc).isoformat()` — the token expires at the instant of creation. No code checks expiration. The plan lists `ZEND_TOKEN_TTL_HOURS` as a configurable but it doesn't exist.

**Risk:** Documentation describing token TTL would be fiction.

**Recommendation:** Document that token expiration is not enforced in milestone 1. Do not reference `ZEND_TOKEN_TTL_HOURS`.

### Finding N1.3: State files use default umask

`os.makedirs(STATE_DIR, exist_ok=True)` creates the state directory with whatever umask the process inherits. On a shared Linux box, `principal.json` and `pairing-store.json` may be world-readable.

**Risk:** Low for single-user home hardware, but the operator quickstart should note this.

**Recommendation:** Operator quickstart should include a note about restricting state directory permissions on shared systems.

## Nemesis Pass 2 — Coupled-State and Protocol Surface Review

### Finding N2.1: Store + spine are not atomic

`pair_client()` writes to `pairing-store.json`, then `cmd_pair()` appends spine events. If the store write succeeds but the spine append fails (disk full, permission error), the pairing record exists without the corresponding event. The systems drift.

**Risk for documentation:** The architecture doc should explain this limitation. The event spine is described as "source of truth" but pairing state lives in a separate file. These are not transactionally consistent.

**Recommendation:** Architecture doc should note: "Store and spine writes are not atomic in milestone 1. The store is the authority for pairing state; the spine records the history."

### Finding N2.2: Event kind filter is broken in CLI

`cli.py:190` passes a string to `spine.get_events(kind=...)`, but `get_events()` calls `kind.value` expecting an `EventKind` enum. Passing a string like `"control_receipt"` would raise `AttributeError`.

**Risk for documentation:** Any API reference that shows `cli.py events --kind control_receipt` would document a command that crashes.

**Recommendation:** This is a code bug. Fix `spine.py:get_events()` to accept either string or enum, or fix `cli.py` to convert the string to `EventKind`. This is a small source fix within the touched surface.

### Finding N2.3: Bootstrap + control capability mismatch

The bootstrap script pairs alice-phone with `['observe']` only. The plan's quickstart then demonstrates `cli.py control --client my-phone --action set_mode --mode balanced`, which requires `control` capability.

**Risk:** A contributor following the quickstart verbatim hits an auth error on the last command.

**Recommendation:** Fix the quickstart to either:
- (a) Use `bootstrap` + separate `pair --device my-phone --capabilities observe,control`, or
- (b) Change the example to `status` instead of `control`

## Code Fix

One code bug was identified within the touched surface that would cause documented commands to fail:

**`spine.py:get_events()` — kind parameter type mismatch.**

The function signature accepts `Optional[EventKind]` but the CLI caller passes a raw string. When `kind` is a non-None string, `kind.value` raises `AttributeError`. The fix is to handle string inputs gracefully.

This fix is deferred — it is documented here but the lane is blocked on plan corrections first. The fix should be applied as part of the implementation pass, not the review.

## Summary

| Dimension | Status |
|-----------|--------|
| Plan structure | Sound |
| Plan accuracy | 7 factual errors — **BLOCKED** |
| Security posture documentation | Would overstate auth — needs correction |
| Milestone ordering | Correct |
| Milestone scope | Correct after endpoint list reduction |
| Code bugs affecting docs | 1 (spine.py kind filter) |
| Specify stage output | Empty (no-op) |

**Verdict:** The lane cannot proceed to implementation until the plan is corrected. The corrections are all editorial (remove phantom endpoints, fix example commands, correct response formats). No architectural changes needed. Estimated correction effort: < 1 hour.
