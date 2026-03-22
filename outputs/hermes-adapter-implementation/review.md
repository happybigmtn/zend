# Hermes Adapter Implementation — Review

Status: **Reviewed with blockers**
Reviewed: 2026-03-22
Reviewer: Claude Opus 4.6
Lane: hermes-adapter-implementation
Files reviewed: hermes.py, daemon.py, cli.py, tests/test_hermes.py, spine.py, store.py

## Summary

The Hermes adapter implements a correct capability-scoped boundary for AI agent
access to the Zend daemon. The core adapter module (hermes.py) is well-structured:
token validation, capability checking, event filtering, and payload stripping all
work correctly. 20 unit tests pass covering the adapter's public surface.

The daemon integration (daemon.py) has four bugs that must be fixed before merge,
and the security model has a known gap that is acceptable for LAN-only milestone 1
but must be resolved before any network exposure.

## Verdict

**Do not merge as-is.** Fix the four blockers below, then the implementation is
milestone-ready.

## Blockers (must-fix)

### B1: Double-call on control endpoints (daemon.py:196-204)

The control endpoint handlers call miner methods twice per request:

    self._send_json(200 if miner.start()["success"] else 400, miner.start())

The first call changes state (starts the miner), then the second call returns
"already_running" failure. Every control command returns a misleading response.

Fix: capture the result once before building the response.

### B2: Duplicate do_GET definition (daemon.py:170-176, 299-310)

Python class bodies silently overwrite duplicate method names. The first do_GET
(line 170) is dead code. The second (line 299) is the live one. If someone edits
the first definition, those changes vanish silently.

Fix: remove the first do_GET definition entirely.

### B3: Pairing tokens expire at issuance (hermes.py:215, 229)

Both the initial pair and re-pair paths set token_expires_at to
datetime.now(timezone.utc).isoformat() — the current time, not a future time.
Every token expires the instant it's created.

Currently masked because the token isn't validated on subsequent requests (see S1),
but this must be fixed for the authority token contract to be meaningful.

Fix: use datetime.now(timezone.utc) + timedelta(hours=24) for expiration.

### B4: Hermes creates orphaned PrincipalId (hermes.py:238-249)

_get_or_create_principal_id reads state/principal.json but falls back to a random
UUID that is never persisted. If Hermes pairs before daemon bootstrap, the Hermes
principal_id diverges from the system's PrincipalId. The product spec requires one
shared PrincipalId across gateway and Hermes.

Fix: use store.load_or_create_principal() instead of _get_or_create_principal_id.

## Should-fix (not blockers)

### S1: Authority token is ceremonial

The /hermes/connect endpoint validates the authority token, but /hermes/status,
/hermes/events, and /hermes/summary authenticate by hermes_id header lookup against
the pairing store. There is no session binding between connect and subsequent
requests. The token system provides no actual security beyond the initial connect
call.

Acceptable for LAN-only milestone 1 if documented. Must be resolved before plan 006
(token auth) or any network exposure.

### S2: /hermes/events query param parsing broken (daemon.py:341)

The path match if self.path == '/hermes/events' uses exact equality, but self.path
includes query strings. A request to /hermes/events?limit=10 falls through to 404.
The limit parameter is never parsed.

### S3: Event over-fetch heuristic can under-deliver

get_filtered_events fetches limit * 2 events then filters. If the spine is
dominated by user_message events, fewer than limit readable events may be returned
even though more exist further back in the journal.

### S4: Payload stripping defaults to pass-through

_strip_sensitive_fields uses an allowlist for control_receipt but passes all other
event kinds through unmodified. Any future event kind added to
HERMES_READABLE_EVENTS would leak its full payload by default.

### S5: No authentication on /hermes/pair

Any HTTP client on the LAN can create a Hermes pairing. Acceptable for LAN-only
milestone 1 where the trust boundary is the network.

## Milestone Fit

The implementation satisfies the product spec's sixth layer (Hermes adapter
boundary) on 7 of 8 requirements:

- Hermes connects through Zend adapter, not directly: met
- Observe-only + summary append in phase 1: met
- Direct miner control through Hermes deferred: met
- Hermes receives only explicitly granted capabilities: met
- Event spine is source of truth: met
- Hermes cannot read user_message events: met
- Pairing endpoint exists: met
- Agent boundary (no authority without explicit grant): partial (token is ceremonial)

## Nemesis Security Findings

### Trust boundary analysis

The adapter enforces capability checks at the function level (hermes.py). The daemon
enforces Hermes identity at the HTTP level via Authorization header. These are two
independent enforcement points — defense in depth.

However, the HTTP-level enforcement relies on header format (prefix "Hermes "), not
cryptographic identity. A LAN attacker who omits the Hermes prefix can reach control
endpoints without any authentication (this is an existing daemon limitation, not
Hermes-specific).

### Privilege escalation

Hermes cannot escalate to control capability. The token parser rejects control at
parse time, and the daemon blocks control endpoints independently via header check.
Two independent barriers.

### Replay and idempotence

Pairing is idempotent (re-pair refreshes token). Authority tokens have no nonce or
binding to a specific session, so they're replayable within their validity window.
Acceptable for LAN-only M1.

### State consistency

Two pairing stores exist (store.py and hermes.py) with independent principal
management. This is the most significant architectural issue — it breaks the shared
PrincipalId invariant. See B4.

### File-system safety

JSON store writes are not atomic (read-modify-write without locking). Concurrent
pairing requests could lose writes. Acceptable for single-user M1.

## Test Coverage Assessment

20 unit tests cover hermes.py's public API well. Missing:

- No HTTP-level integration tests for daemon endpoints
- No test for B1 (double-call bug)
- No test for B2 (duplicate do_GET)
- No test for B3 (token expiration on pair)
- No test for B4 (PrincipalId divergence)
- No test for S2 (query param parsing)
- No test for Hermes attempting control commands via HTTP

## What the Implementation Gets Right

1. Capability boundary is correctly modeled as an explicit allowlist
2. Event filtering uses positive allowlist (HERMES_READABLE_EVENTS), not denylist
3. Payload stripping uses field-level allowlist for sensitive event kinds
4. Token validation rejects unknown capabilities at parse time
5. Pairing is idempotent by design
6. CLI integration provides a complete Hermes command surface
7. Tests cover the adapter module's critical paths thoroughly
