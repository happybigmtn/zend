All 19 tests pass. Now I have complete context. Let me produce the review.

---

# Hermes Adapter Implementation — Nemesis Review

## Overall Assessment

The slice delivers a structurally correct capability boundary: Hermes gets `observe` + `summarize`, cannot issue control commands, and cannot read `user_message` events. Tests pass. The API surface matches the spec. But there are **security flaws and logical inconsistencies** that would be dangerous if carried forward unchecked into later milestones.

---

## Pass 1 — First-Principles Challenge

### CRITICAL: Token is expired at birth

`★ Insight ─────────────────────────────────────`
This is the most consequential bug in the slice. It "works" only by accident.
`─────────────────────────────────────────────────`

`hermes.py:93` — `_generate_authority_token` sets `expires_at` to `datetime.now()`:

```python
'expires_at': datetime.now(timezone.utc).isoformat(),
```

And `pair_hermes()` at line 159 does the same for `token_expires_at`. The token is expired **the instant it's created**. The only reason `connect()` succeeds is because `_is_token_expired()` has a 60-second grace period (line 132):

```python
return grace_period < -60  # Expired if more than 60 seconds ago
```

So tokens are "valid" for ~60 seconds after issuance, but this is an **accident**, not a design choice. The `expires_at` should be set to `now() + timedelta(hours=N)`.

### CRITICAL: `validate_connection_auth()` bypasses all token validation

`hermes.py:326-346` — This function constructs a `HermesConnection` directly from the pairing record, with **no token expiration check**:

```python
def validate_connection_auth(hermes_id: str) -> Optional[HermesConnection]:
    pairing = get_pairing(hermes_id)
    if not pairing:
        return None
    return HermesConnection(...)
```

All operational endpoints (`GET /hermes/status`, `POST /hermes/summary`, `GET /hermes/events`) use this function via the `Authorization: Hermes <hermes_id>` header. This means:

1. Pair a Hermes agent → pairing record created
2. Token expires
3. Hermes **still has permanent access** to all operational endpoints

The token-based auth (`POST /hermes/connect`) and the header-based auth (everything else) are **two disconnected trust models**. The connect flow is effectively unused by the operational endpoints.

### HIGH: Control command denylist is fragile

`daemon.py:349-356`:

```python
if self.path in ['/miner/start', '/miner/stop', '/miner/set_mode']:
    self._send_json(403, ...)
```

This is a **denylist**. Any new control endpoint (e.g., `/miner/restart`, `/miner/reboot`, `/miner/config`) added later won't be blocked. Should be an **allowlist**: for any request with `Authorization: Hermes`, only permit `/hermes/*` paths.

### HIGH: Public `/status` endpoint makes `observe` capability decorative

The `GET /status` endpoint in `daemon.py:272` returns the full miner snapshot with no auth. Hermes can call it directly instead of `GET /hermes/status`. The capability check on the Hermes path is bypass-able by omitting the Hermes header.

For LAN-only M1 this may be acceptable (all local clients see status), but the spec says "Hermes can observe miner status" as a scoped capability. In reality, **anyone on the LAN** can observe status — the Hermes `observe` check adds nothing.

### MEDIUM: Token is unsigned — forgeable by any LAN peer

The review doc acknowledges this (Decision 3). For M1 on LAN this is acceptable, but the `POST /hermes/connect` endpoint's token validation provides **zero actual authentication**. Any process that knows the base64-JSON format can forge a token with arbitrary capabilities. This should not be carried past M1.

---

## Pass 2 — Coupled-State Review

### HIGH: Hermes pairing emits no spine event

Gateway pairing (`cli.py:cmd_pair`) appends `pairing_requested` and `pairing_granted` events. Hermes pairing (`POST /hermes/pair` in daemon.py:306-323) creates only the pairing record — **no events are emitted**. Hermes pairing is invisible in the audit trail. This breaks the spec's stated invariant that the event spine is the source of truth.

### MEDIUM: `token_used` is never set to `True`

`HermesPairing.token_used` (hermes.py:65) defaults to `False`. After `connect()` succeeds, it's never updated. If this was intended for single-use token enforcement, it's broken. If it's unused, it's dead state that will confuse future readers.

### MEDIUM: `token_expires_at` in pairing record vs `expires_at` in token payload diverge

`pair_hermes()` generates `expires` at line 159, then calls `_generate_authority_token()` which generates its own `expires_at` at line 93. These are separate `datetime.now()` calls and will differ by microseconds. The pairing record stores one timestamp; the token carries a different one. Only the token's value is checked by `connect()`.

### MEDIUM: Race condition in pairing store under `ThreadedHTTPServer`

`_load_hermes_pairings()` / `_save_hermes_pairings()` are read-then-write without locking. The daemon uses `ThreadedHTTPServer` (daemon.py:376), so concurrent `POST /hermes/pair` requests can lose data. Acceptable for M1 but should be noted.

### LOW: `get_filtered_events` over-fetch heuristic is lossy

`hermes.py:315` fetches `limit * 2` events then filters. If >50% of events are non-Hermes-readable (e.g., `user_message`, `pairing_requested`, `pairing_granted`), the function returns fewer than `limit` results even when more eligible events exist in the spine. The 2x multiplier is a heuristic, not a guarantee.

### LOW: `read_status` fallback masks integration failures

`hermes.py:248-260` catches `ImportError` on `from daemon import miner` and returns a dummy dict. The test (`test_read_status_with_observe_capability`) exercises only this fallback path, not the real miner integration. The test proves the permission check works, but not the data path.

### LOW: CLI truncation crash risk

`cli.py:226` — `result.get('authority_token')[:50]` will raise `TypeError` if the key is absent. The error-path guard above should prevent this, but it's fragile.

---

## Milestone Fit

The slice delivers what it promises: a capability boundary module with tests. It fits the milestone 1 goal of establishing the Hermes adapter contract. The API shape is correct and matches the spec.

**What's real**: Capability constants, event filtering allowlist, permission checks on `read_status`/`append_summary`, idempotent pairing, test coverage of the boundary.

**What's theater**: Token expiration (broken), connect vs header auth (disconnected), control command denylist (fragile), `observe` capability (bypass-able via public endpoint).

---

## Remaining Blockers (for next slice)

| Blocker | Severity | Fix |
|---------|----------|-----|
| Token expires at birth | Critical | Set `expires_at` to `now() + timedelta(hours=1)` |
| `validate_connection_auth` ignores token state | Critical | Check token expiration or introduce session concept |
| Control denylist → allowlist | High | For Hermes auth, only permit `/hermes/*` paths |
| No spine event on Hermes pairing | High | Call `append_pairing_granted` equivalent |
| `token_used` never set | Medium | Either implement or remove the field |
| Timestamps diverge between pairing record and token | Medium | Generate once, pass to both |

---

## Verdict

**Accept with caveats.** The structural boundary is correct and the test suite proves the happy paths and permission denials. The token/auth layer is broken in ways that don't matter for a LAN-only simulator but **must not** be carried forward. The critical items above should be logged as explicit tech debt with ownership for the next slice.

`★ Insight ─────────────────────────────────────`
The core design decision — adapter as in-process capability boundary, not a deployment boundary — is sound. Keeping Hermes in the same process means the trust boundary is enforced by code, not by network isolation. The allowlist approach for readable event kinds (`HERMES_READABLE_EVENT_KINDS`) is correct: new event types are blocked by default until explicitly added. The denylist approach for control commands is the opposite and should be flipped.
`─────────────────────────────────────────────────`