# Hermes Adapter Implementation — Nemesis Review

**Review Date**: 2026-03-22
**Reviewer**: Nemesis (security-focused)
**Lane**: hermes-adapter-implementation
**Verdict**: CONDITIONALLY APPROVED — fixes applied during review

## Summary

The Hermes adapter establishes a capability-scoped boundary between the Hermes AI agent and the Zend gateway contract. The adapter itself is structurally sound: capability enforcement, event filtering, and token validation work as specified. However the original review was a rubber-stamp ("no issues identified") and missed a fail-open security default, a dead code path in the CLI, and a private API import that breaks encapsulation.

Five fixes were applied during this review. All 18 tests pass post-fix.

## Fixes Applied

| ID | Severity | File | Change |
|----|----------|------|--------|
| S1 | CRITICAL | `hermes.py:101-103` | `is_token_expired` now returns `True` (expired) on unparseable dates — fail closed instead of fail open |
| C1 | HIGH | `cli.py:243-271` | Removed dead `daemon_call` in `cmd_hermes_status` that fired an unauthenticated request before the real one |
| C2 | MEDIUM | `hermes.py:214-230` | `get_filtered_events` now uses public `spine.get_events()` instead of private `spine._load_events` |
| C3 | LOW | `hermes.py:250` | Removed dead `existing` variable in `pair_hermes` |
| CS2 | LOW | `tests/test_hermes.py:42-47` | `setUp` now cleans spine file alongside pairing file for test isolation |

## Open Issues (NOT fixed — outside touched surface or needs design decision)

### S2 HIGH: Miner control endpoints have no auth

`/miner/start`, `/miner/stop`, `/miner/set_mode` execute unconditionally. The plan's proof claims `curl -X POST /miner/start -H "Authorization: Hermes hermes-001"` returns 403, but it returns 200. The Hermes adapter correctly scopes `/hermes/*` endpoints, but nothing prevents Hermes (or any LAN client) from calling miner endpoints directly.

**Impact**: The adapter boundary is a gentleman's agreement — enforceable only if the caller voluntarily uses `/hermes/*` paths.

**Recommendation**: Add auth middleware to miner control endpoints in a follow-up plan. At minimum, reject requests bearing a `Hermes` auth scheme on non-Hermes paths.

### S3 LOW: `active_hermes_connections` unbounded

In-memory dict in `daemon.py:159` grows without eviction. No TTL, no size cap. Minor DoS vector under sustained pairing/connect cycles.

**Recommendation**: Add TTL-based eviction or cap the dict size.

### CS1 MEDIUM: Race conditions on pairing file I/O

`ThreadedHTTPServer` + non-atomic read-modify-write on `hermes-pairing-store.json`. Concurrent pair requests can cause lost writes.

**Recommendation**: Use file locking (`fcntl.flock`) or atomic rename-on-write in a follow-up.

## Security Analysis

### Trust Boundaries (Pass 1)

| Boundary | Status | Notes |
|----------|--------|-------|
| Token validation | **PASS** (after S1 fix) | Expired, missing, and unparseable tokens now all fail closed |
| Capability checking | **PASS** | `connect()` rejects any capability not in `HERMES_CAPABILITIES` |
| Event filtering | **PASS** | `user_message` correctly excluded from Hermes reads |
| Control rejection | **PARTIAL** | Enforced on `/hermes/*` paths; unenforced on `/miner/*` (see S2) |
| Token revocation | **PASS** | Sets expiration to epoch; validated on next use |

### Coupled State (Pass 2)

| Surface | Status | Notes |
|---------|--------|-------|
| Pairing idempotency | **PASS** | Re-pair generates new token, overwrites old record |
| Spine append-only | **PASS** | No mutation or deletion paths |
| Token ↔ connection consistency | **PASS** | Connection created from validated pairing; token carried for cache lookup |
| File I/O concurrency | **FLAG** | See CS1 — not safe under concurrent threaded access |
| Test isolation | **PASS** (after CS2 fix) | Both state files cleaned between tests |

### Capability Escalation Paths

1. **Direct store manipulation**: If an attacker can write to `hermes-pairing-store.json`, they can grant themselves any capability. Mitigated by filesystem permissions (state dir is local).

2. **Stale in-memory connection**: `active_hermes_connections` caches connections after `connect()`. If a token is revoked, the cached connection remains valid until the daemon restarts. Acceptable for MVP; production should invalidate cached connections on revocation.

3. **hermes_id predictability**: `hermes_id` is user-chosen (e.g., `hermes-001`). Auth relies on the UUID token, not the ID. No escalation path here.

## Milestone Fit

| Plan Task | Status | Notes |
|-----------|--------|-------|
| Create hermes.py adapter module | DONE | |
| HermesConnection with token validation | DONE | Fixed fail-open default |
| readStatus through adapter | DONE | |
| appendSummary through adapter | DONE | |
| Event filtering (block user_message) | DONE | |
| Hermes pairing endpoint | DONE | |
| CLI Hermes subcommands | DONE | Fixed dead request in status cmd |
| Tests | DONE | 18/18 pass, improved isolation |
| Gateway Agent tab update | NOT STARTED | UI task, deferred per spec |

## Remaining Blockers

1. **S2** must be addressed before any deployment where Hermes and the daemon share a network boundary without additional segmentation. This is a follow-up plan item, not a blocker for the adapter itself.

## Test Evidence

```
18 passed in 0.04s (post-fix)
```
