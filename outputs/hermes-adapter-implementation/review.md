# Hermes Adapter Implementation — Nemesis Review

**Date:** 2026-03-22
**Reviewer:** Nemesis-style security review (independent)
**Lane:** `hermes-adapter-implementation`
**Verdict:** BLOCKED — 3 critical findings, 2 high, 4 medium

## Executive Summary

The adapter's core design is sound: separate capability namespace, event filtering,
independent pairing store. The spec accurately describes the intended boundary.
However, the daemon integration layer has a **runtime crash** that prevents two of
three operational endpoints from functioning, a **dual auth model** that makes token
validation ceremonial, and a **state directory split** that silently partitions
Hermes state from the rest of the system when `ZEND_STATE_DIR` is unset.

The 16 unit tests pass because they exercise adapter functions directly (passing
`HermesConnection` dataclass objects) and test daemon logic only at the regex/logic
level. No test sends an actual HTTP request to a running daemon. The smoke test
uses CLI paths that avoid the daemon entirely. As a result, the test suite provides
high confidence in the adapter module but zero confidence in the daemon integration.

---

## Pass 1 — First-Principles Challenge

### C1 (Critical): Runtime type mismatch — `/hermes/status` and `/hermes/summary` crash on invocation

**Location:** `daemon.py:171-201` vs `hermes.py:384-413,416-450`

The daemon's `_require_hermes_auth()` returns a `dict`:
```python
return {
    "hermes_id": hermes_id,
    "principal_id": pairing.principal_id,
    "capabilities": pairing.capabilities,
}
```

The adapter functions `read_status()` and `append_summary()` expect a
`HermesConnection` dataclass and access `.capabilities`, `.hermes_id`,
`.principal_id` via attribute notation. Attribute access on a dict raises
`AttributeError`. Confirmed experimentally:

```
>>> conn_dict = {"hermes_id": "test", "capabilities": ["observe"]}
>>> conn_dict.capabilities
AttributeError: 'dict' object has no attribute 'capabilities'
```

`get_filtered_events()` happens to work because it never accesses `connection`
attributes — the parameter is accepted but unused.

**Impact:** Two of the three operational Hermes HTTP endpoints crash immediately
on any request. The adapter's capability boundary is never reached.

**Why tests miss this:** `TestHermesAdapterDaemon` tests regex matching and
adapter logic separately, never sending HTTP requests. The adapter tests
construct `HermesConnection` objects directly.

**Fix:** Either have `_require_hermes_auth` return a `HermesConnection`, or
have the daemon construct one from the dict before passing to adapter functions.

---

### C2 (Critical): Dual auth model — daemon bypasses token validation entirely

**Location:** `daemon.py:171-201` (header auth) vs `hermes.py:337-377` (token auth)

The system has two independent auth paths:

| Path | Auth mechanism | Enforces expiration | Enforces per-token capabilities |
|------|---------------|--------------------|---------------------------------|
| CLI (`hermes status --token`) | Authority token (base64 JSON) | Yes | Yes |
| HTTP (`GET /hermes/status`) | `Authorization: Hermes <id>` header | No | No |

The daemon's operational endpoints (`/hermes/status`, `/hermes/summary`,
`/hermes/events`) use `_require_hermes_auth()`, which only checks that a
pairing record exists for the `hermes_id`. It does not validate or even require
an authority token. The `/hermes/connect` endpoint validates the token, but the
result is not stored server-side and is never checked by subsequent requests.

**Consequence:**
1. After pairing (unauthenticated), Hermes can operate indefinitely with
   `Authorization: Hermes <id>` — no token needed
2. Token expiration (`TOKEN_VALIDITY_SECONDS = 86400`) has no effect on
   operational access
3. Per-token capability scoping is illusory — the daemon always uses the
   pairing's full `HERMES_CAPABILITIES`
4. The connect step is ceremonial

Confirmed experimentally: pair → skip token issuance → call endpoints with
just the header → full access granted.

**Fix:** Either enforce token-based auth on all operational endpoints (pass
token in header, validate per-request), or document that pairing-based auth
is the intended model and remove the token validation ceremony.

---

### C3 (Critical): State directory mismatch — hermes.py resolves to wrong path

**Location:** `hermes.py:100-102` vs `daemon.py:29-30`, `spine.py:18-19`, `store.py:21-22`

```python
# hermes.py — parents[1] → services/state
Path(__file__).resolve().parents[1] / "state"

# daemon.py, spine.py, store.py — parents[2] → <repo_root>/state
Path(__file__).resolve().parents[2] / "state"
```

All four modules are in `services/home-miner-daemon/`. The daemon, spine, and
store correctly resolve `parents[2]` to reach `<repo_root>/state`. But hermes.py
uses `parents[1]`, resolving to `services/state` — a completely different directory.

When `ZEND_STATE_DIR` is set (as in tests and smoke test), all modules converge.
When it is unset (default operation), hermes pairing records and authority token
journals silently write to `services/state/` while the spine, principal, and
gateway pairings write to `<repo_root>/state/`. This means:
- `pair_hermes()` creates a record that `_require_hermes_auth()` can find
  (both use hermes module), but the principal fetched by `store.load_or_create_principal()`
  during pairing comes from a different directory than the one the daemon uses
- The hermes pairing store and the gateway pairing store are not collocated

**Fix:** Change `hermes.py:102` from `parents[1]` to `parents[2]`.

---

## Pass 2 — Coupled-State Review

### H1 (High): `/hermes/pair` is unauthenticated — any local process can gain access

**Location:** `daemon.py:258-273`

The pairing endpoint requires no authentication. Any process on the bind
interface can POST to `/hermes/pair` with an arbitrary `hermes_id` and
immediately gain a pairing record. Combined with C2 (header-only auth on
operational endpoints), this means any localhost process can:

1. `POST /hermes/pair {"hermes_id": "rogue"}` → pairing created
2. `GET /hermes/status` with `Authorization: Hermes rogue` → miner status

The daemon defaults to `127.0.0.1`, which limits exposure to localhost. But
the env var `ZEND_BIND_HOST` can expose it on LAN, where any device could
pair autonomously.

**Mitigation in milestone 1:** Localhost-only binding. But this should be
explicitly documented as a trust assumption, and the spec should note that
LAN deployment requires a pairing approval gate.

---

### H2 (High): No revocation mechanism — paired Hermes agents persist forever

**Location:** `hermes.py` (no `unpair_hermes` or `revoke_hermes` function exists)

The spine defines `EventKind.CAPABILITY_REVOKED` but no code path produces or
consumes it. Once a Hermes agent is paired, it cannot be revoked through any
API, CLI command, or HTTP endpoint. The only way to remove a pairing is to
manually delete entries from `hermes-pairing-store.json`.

If a Hermes agent is compromised, the operator has no way to disconnect it
without stopping the daemon and editing state files.

**Fix:** Add `unpair_hermes(hermes_id)` function and corresponding
`/hermes/unpair` endpoint and CLI command.

---

### M1 (Medium): Authority tokens are forgeable with known principal_id

**Location:** `hermes.py:143-193`

Authority tokens are base64 JSON with no cryptographic signature, HMAC, or
shared secret. The only "secret" is the `principal_id` (a UUID). Once
disclosed — via any legitimate token (base64-decodable), via the
`/hermes/connect` response, or via filesystem access — an attacker can forge
tokens with arbitrary capabilities and expiration dates.

Confirmed experimentally: forged a token with `expires_at: 2099-01-01` that
was accepted by `connect()`.

**Acknowledged as milestone-1 scope.** The spec explicitly marks this for JWT
upgrade. However, combined with C2 (token validation is bypassed anyway),
this is currently inert — the real auth is pairing-based, not token-based.

---

### M2 (Medium): `/hermes/events` does not check `observe` capability

**Location:** `daemon.py:226-231`

The `/hermes/status` endpoint checks `observe` capability via
`_hermes_check_capability(conn, 'observe')`. The `/hermes/events` endpoint
does not. A Hermes connection with only `summarize` capability could read
filtered events.

In practice this is benign because all pairings grant full
`HERMES_CAPABILITIES`, but it violates the least-privilege principle described
in the spec.

---

### M3 (Medium): Dead code in `connect()` — unused expiration computation

**Location:** `hermes.py:365-369`

```python
now = datetime.now(timezone.utc)
expires = datetime.fromtimestamp(
    now.timestamp() + TOKEN_VALIDITY_SECONDS,
    tz=timezone.utc
)
```

This computes a new expiration that is never assigned or returned. The
`HermesConnection` uses `token.expires_at` (line 376), not `expires`.
Harmless but confusing — suggests a copy-paste from `pair_hermes()`.

---

### M4 (Medium): State file operations are not concurrency-safe

**Location:** `hermes.py:112-140`

`_load_hermes_pairings()` / `_save_hermes_pairings()` perform non-atomic
read-modify-write cycles. The daemon uses `ThreadedHTTPServer`, so concurrent
requests could cause lost pairing updates. The JSONL token journal
(`_save_authority_token`) is append-only but also lacks file locking.

**Impact in milestone 1:** Low, since Hermes pairing is rare and typically
single-threaded. Would need fixing before any multi-agent deployment.

---

## Test Coverage Assessment

| Surface | Covered | Gap |
|---------|---------|-----|
| Adapter token validation | Yes | — |
| Adapter capability enforcement | Yes | — |
| Adapter event filtering | Yes | — |
| Adapter idempotent pairing | Yes | — |
| Daemon HTTP endpoint integration | **No** | All `TestHermesAdapterDaemon` tests test logic, not HTTP |
| Daemon type compatibility (dict vs HermesConnection) | **No** | Not tested; crashes at runtime |
| State directory resolution | **No** | Tests set `ZEND_STATE_DIR`, masking the bug |
| Token forgery resistance | **No** | No test attempts forged token |
| Revocation | **No** | No revocation code exists |
| Concurrent access | **No** | Single-threaded tests only |

---

## Milestone Fit

The adapter correctly implements the intended capability boundary at the
module level. The CLI path works end-to-end. The spec and acceptance criteria
are well-written and accurate for the adapter functions.

However, the daemon integration is broken (C1), the auth model is inconsistent
(C2), and the state directory diverges silently (C3). These three findings mean
the HTTP API — the path any external Hermes agent would actually use — does not
work as specified.

**Recommendation:** Fix C1, C2, C3 before merging. H1 and H2 can be tracked
as follow-up work with explicit documentation of the trust assumptions.

---

## Blockers (must fix before merge)

| # | Finding | Fix |
|---|---------|-----|
| C1 | `_require_hermes_auth` returns dict, adapter expects HermesConnection | Return HermesConnection or construct one in daemon |
| C2 | Operational endpoints bypass token validation | Choose one auth model and enforce it consistently |
| C3 | `hermes.py` state dir uses `parents[1]` instead of `parents[2]` | Change to `parents[2]` to match daemon/spine/store |

## Follow-up (track, don't block)

| # | Finding | Tracking |
|---|---------|----------|
| H1 | Unauthenticated pairing | Document trust assumption; gate before LAN deploy |
| H2 | No revocation | Add `unpair_hermes` function and endpoint |
| M1 | Forgeable tokens | JWT upgrade (already planned) |
| M2 | Events endpoint skips observe check | Add capability check |
| M3 | Dead code in connect() | Delete unused computation |
| M4 | Non-atomic state file ops | Add file locking before multi-agent |
