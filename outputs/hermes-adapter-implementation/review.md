# Hermes Adapter — Slice Review

**Lane:** `hermes-adapter-implementation`
**Date:** 2026-03-22
**Stage:** First honest review
**Supervisor:** Polish pass

## Summary

First reviewed slice for the Hermes adapter. The slice delivers a clean, in-process adapter that scopes Hermes agents to `observe + summarize` capabilities and enforces three hard boundaries: no control commands, no `control` capability in tokens, and no `user_message` event exposure. The implementation is structurally correct; this review is a correctness and precision pass.

## Artifacts Produced

| Artifact | Path | Status |
|----------|------|--------|
| Implementation spec | `outputs/hermes-adapter-implementation/spec.md` | Updated (this cycle) |
| Adapter module | `services/home-miner-daemon/hermes.py` | 233 lines |
| Daemon | `services/home-miner-daemon/daemon.py` | 274 lines |
| CLI | `services/home-miner-daemon/cli.py` | 302 lines |
| Event spine | `services/home-miner-daemon/spine.py` | 153 lines |
| Pairing store | `services/home-miner-daemon/store.py` | 136 lines |

## Verification

### Adapter module

```bash
cd services/home-miner-daemon
python3 hermes.py
# Expected output:
#   Capabilities: ['observe', 'summarize']
#   Readable events: ['hermes_summary', 'miner_alert', 'control_receipt']
```

### Token validation

`connect()` in `hermes.py` validates in order:

1. Four pipe-delimited fields present
2. ISO 8601 expiration not in the past
3. Both `observe` and `summarize` in capabilities list
4. `control` **not** in capabilities list (raises `PermissionError` if present)

```python
# Token format: hermes_id|principal_id|capabilities|expires_at
# Example: hermes-001|abc123|observe,summarize|2027-12-31T23:59:59+00:00
```

### Control rejection (daemon.py)

Control routes (`/miner/start`, `/miner/stop`, `/miner/set_mode`) are handled in `GatewayHandler.do_POST`. Before dispatching to the miner operation, the handler checks:

```python
if self.path in ['/miner/start', '/miner/stop', '/miner/set_mode']:
    if _extract_hermes_auth(self.headers):
        self._send_json(403, {
            "error": "HERMES_UNAUTHORIZED",
            "message": "Hermes cannot issue control commands"
        })
        return
```

This is a direct if-guard in `do_POST`, not route-layer middleware. The check runs before `miner.start()`, `miner.stop()`, or `miner.set_mode()` is called.

### Event filtering

`get_filtered_events()` in `hermes.py` calls `get_events(limit=limit * 2)` from `spine.py` then filters:

```python
readable_kinds = [k.value for k in HERMES_READABLE_EVENTS]
filtered = [e for e in all_events if e.kind in readable_kinds]
```

`EventKind.USER_MESSAGE` is not in `HERMES_READABLE_EVENTS`, so it is never returned to Hermes. The filter cannot be bypassed through a different API path because all Hermes reads route through this function.

### Capability enforcement per function

| Function | Required capability | Error on violation |
|----------|--------------------|--------------------|
| `read_status()` | `observe` | `PermissionError` |
| `append_summary()` | `summarize` | `PermissionError` |
| `get_filtered_events()` | any active connection | `ValueError` at `connect()` |

## Boundary Enforcement Matrix

| Boundary | Implemented | Evidence |
|----------|-------------|----------|
| Control commands blocked | ✓ | `daemon.py` `do_POST` guard, 403 response |
| `control` in token rejected | ✓ | `hermes.py` `connect()` raises `PermissionError` |
| `user_message` not readable | ✓ | `hermes.py` `get_filtered_events()` filter |
| Token expiration enforced | ✓ | `hermes.py` `_is_token_expired()` |
| `observe` required for status | ✓ | `hermes.py` `read_status()` check |
| `summarize` required for write | ✓ | `hermes.py` `append_summary()` check |
| Pairing idempotent | ✓ | `hermes.py` `pair_hermes()` re-pairs on same `hermes_id` |

## Design Decisions

1. **Adapter in-process, not a separate service.**
   `hermes.py` is imported directly by `daemon.py`. There is no inter-process communication or separate trust boundary. This keeps the enforcement simple and auditable at a single call site per operation.

2. **`control` rejected at `connect()`, not at each operation.**
   If a token contains `control`, it is rejected immediately when the connection is established. This means a compromised token cannot be used for any operation, including those that forget to check.

3. **`user_message` filter is in the adapter, not the spine.**
   The spine (`spine.py`) is intentionally unopinionated about which reader consumes which events. Filtering in the adapter keeps the spine simple and means the filter travels with the consumer identity, not the storage layer.

4. **Pipe-delimited token for milestone 1.**
   The token format (`hermes_id|principal_id|capabilities|expires_at`) is human-readable and avoids a JWT dependency. The format is documented in the spec so a future JWT migration is a mechanical replacement of `connect()`.

5. **Active connections in-memory for milestone 1.**
   `active_hermes_connections` is a `dict` in `daemon.py`. A future session store (Redis, SQLite) replaces this without changing any interface.

## Findings

### Finding 1 — Control rejection is an if-guard, not middleware

The spec and review previously described control rejection as "route-layer middleware." This was imprecise. The check is a direct `if` statement inside `GatewayHandler.do_POST` that runs before the miner operation is dispatched. It is functionally equivalent to middleware for this use case, but the implementation is more explicit and easier to audit: a reader can see the exact path of execution without understanding Python middleware patterns.

**Impact:** Low. Behavior is correct. Terminology in spec and review is now precise.

### Finding 2 — `hermes.py` `get_hermes_status()` defined but not wired to daemon endpoint

`get_hermes_status()` exists in `hermes.py` (returns connection info + recent summaries) but the daemon's `/hermes/status` endpoint calls `hermes_read_status()` (which returns the miner snapshot) instead. The two functions serve different purposes — one for the daemon status page, one for the Hermes agent. The naming overlap is confusing.

**Impact:** Low. Both functions are correct for their respective callers. Renaming `get_hermes_status()` to `get_hermes_connection_status()` in a future cleanup would reduce confusion.

### Finding 3 — Token has no integrity mechanism

The authority token is a plain text pipe-delimited string with no signature or HMAC. Anyone who has the token string can use it. For milestone 1 (LAN-only daemon, trusted agents), this is acceptable. For production, the token must be replaced with a signed JWT so that token forgery is impossible.

**Impact:** Accepted for milestone 1. Documented in spec's "Future Expansion" section.

## Next Steps

1. **Write `services/home-miner-daemon/tests/test_hermes.py`**
   - Test `connect()` with valid token, expired token, malformed token, and `control`-in-token
   - Test `read_status()` with and without `observe`
   - Test `append_summary()` with and without `summarize`
   - Test `get_filtered_events()` confirms `user_message` is excluded

2. **Update smoke test `scripts/hermes_summary_smoke.sh`** against live daemon
   - Pair → connect → status → summary → events → control rejection

3. **Rename `get_hermes_status()` → `get_hermes_connection_status()`**
   - Reduces naming confusion with the daemon status endpoint

4. **Add structured logging for Hermes events**
   - Per observability spec: log each Hermes read/write with `hermes_id`, `kind`, and capability used

## Lessons Learned

- Keeping the Hermes adapter in-process with the daemon makes boundary enforcement trivial to audit: every Hermes operation goes through `hermes.py` before touching `spine.py`.
- The `control` capability check at `connect()` time is a stronger design than per-operation checks: it fails closed rather than relying on every future operation to remember to check.
- The pipe-delimited token format is easy to debug but must be replaced before any production deployment. The migration path is documented.
