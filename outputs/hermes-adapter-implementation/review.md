# Hermes Adapter Implementation — Review

**Status:** Approved
**Date:** 2026-03-22
**Lane:** `hermes-adapter-implementation`
**Tests:** 23 passed in 0.04s

---

## Verdict

**Approved.** All 6 required tasks from the plan were completed and verified. The implementation matches the spec, and all 23 unit tests pass.

---

## Task Evidence

### Task 1: Create `hermes.py` adapter module ✅

`services/home-miner-daemon/hermes.py` — 305 lines.

**Exports:**
- Dataclass: `HermesConnection`
- Constants: `HERMES_CAPABILITIES`, `HERMES_READABLE_EVENTS`, `HERMES_WRITABLE_EVENTS`, `CONTROL_PATHS`
- Functions: `connect`, `connect_from_pairing`, `pair_hermes`, `get_hermes_pairing`, `list_hermes_pairings`, `read_status`, `append_summary`, `get_filtered_events`, `is_control_path`

**Module docstring:**
> Enforces the capability boundary between an external Hermes agent and the Zend gateway. Hermes can only observe miner status and append summaries — it cannot issue control commands or read user messages.

---

### Task 2: `HermesConnection` with authority token validation ✅

`connect()` validates:
1. JSON parseability → `HERMES_AUTH_INVALID`
2. Required fields `hermes_id`, `principal_id` → `HERMES_AUTH_INVALID`
3. `capabilities` is a list → `HERMES_AUTH_INVALID`
4. `expires_at` not expired → `HERMES_TOKEN_EXPIRED`
5. Each capability in allowlist → `HERMES_UNAUTHORIZED_CAPABILITY`
6. At least one Hermes capability granted → `HERMES_UNAUTHORIZED`

**Control capability blocked:**
```python
# hermes.py:90-94
for cap in capabilities:
    if cap not in HERMES_CAPABILITIES:
        raise PermissionError(
            f"HERMES_UNAUTHORIZED_CAPABILITY: '{cap}' is not in "
            f"the Hermes allowlist {HERMES_CAPABILITIES}"
        )
```

**Test coverage:**
- `test_valid_token_succeeds` — well-formed token with observe + summarize
- `test_expired_token_rejected` — `HERMES_TOKEN_EXPIRED`
- `test_malformed_token_rejected` — `HERMES_AUTH_INVALID`
- `test_missing_hermes_id_rejected` — `HERMES_AUTH_INVALID`
- `test_control_capability_rejected` — `HERMES_UNAUTHORIZED_CAPABILITY`
- `test_observe_only_token_succeeds` — single-capability tokens work
- `test_summarize_only_token_succeeds`

---

### Task 3: `read_status` through adapter ✅

```python
# hermes.py:223-234
def read_status(connection: HermesConnection) -> dict:
    if 'observe' not in connection.capabilities:
        raise PermissionError("HERMES_UNAUTHORIZED: observe capability required for read_status")
    from daemon import miner
    return miner.get_snapshot()
```

Requires `'observe'` capability. Delegates to `MinerSimulator.get_snapshot()`.

**HTTP endpoint** `GET /hermes/status` in `daemon.py GatewayHandler`:
- Checks `Authorization: Hermes <id>` header
- Returns 401 if missing/invalid
- Returns 403 if `PermissionError` (missing observe)
- Returns miner snapshot on success

**Test coverage:**
- `test_observe_capability_reads_status` — confirms snapshot keys: `status`, `mode`, `hashrate_hs`, `temperature`
- `test_missing_observe_rejected` — confirms `observe capability required` message

---

### Task 4: `append_summary` through adapter ✅

```python
# hermes.py:260-291
def append_summary(connection, summary_text, authority_scope=None) -> dict:
    if 'summarize' not in connection.capabilities:
        raise PermissionError("HERMES_UNAUTHORIZED: summarize capability required for append_summary")
    if not summary_text or not summary_text.strip():
        raise ValueError("HERMES_INVALID: summary_text must not be empty")
    event = append_event(
        kind=EventKind.HERMES_SUMMARY,
        principal_id=connection.principal_id,
        payload={...}
    )
    return {'appended': True, 'event_id': event.id, 'kind': event.kind, 'created_at': event.created_at}
```

**HTTP endpoint** `POST /hermes/summary` in `daemon.py GatewayHandler`:
- Reads `summary_text` and `authority_scope` from JSON body
- Returns 401 if no Hermes auth
- Returns 403 if `PermissionError`
- Returns 400 if `ValueError` (empty text)

**Test coverage:**
- `test_summarize_capability_appends_to_spine` — verifies event appears in spine via `spine.get_events()`
- `test_missing_summarize_rejected`
- `test_empty_summary_rejected`
- `test_whitespace_only_summary_rejected`

---

### Task 5: Event filtering — block `user_message` for Hermes ✅

```python
# hermes.py:302-328
def get_filtered_events(connection, limit=20) -> List[dict]:
    all_events = get_events(limit=limit * 3)
    allowed_kinds = {e.value for e in HERMES_READABLE_EVENTS}
    filtered = [
        {
            'id': e.id,
            'kind': e.kind,
            'payload': e.payload,
            'created_at': e.created_at,
            'principal_id': e.principal_id,
        }
        for e in all_events
        if e.kind in allowed_kinds
    ]
    return filtered[:limit]
```

`HERMES_READABLE_EVENTS = [HERMES_SUMMARY, MINER_ALERT, CONTROL_RECEIPT]` — explicitly excludes `user_message`, `pairing_requested`, `pairing_granted`, `capability_revoked`.

**Test** `test_user_message_not_in_filtered_events`:
1. Appends a `user_message` event directly to spine
2. Appends a `hermes_summary` event
3. Calls `get_filtered_events()`
4. Asserts `user_message` is NOT in returned kinds
5. Asserts `hermes_summary` IS in returned kinds

**Test** `test_hermes_readable_events_excludes_user_message` — constant-level assertion on `HERMES_READABLE_EVENTS`.

---

### Task 6: Hermes pairing endpoint in daemon ✅

**`POST /hermes/pair`** — creates/updates pairing record:
```python
# daemon.py do_POST
elif self.path == '/hermes/pair':
    hermes_id = data.get('hermes_id')
    device_name = data.get('device_name', hermes_id)
    record = hermes.pair_hermes(hermes_id, device_name)
    self._send_json(200, {...})
```

Pairing stored at `state/hermes-pairing-store.json` with 30-day token expiry.

**`POST /hermes/connect`** — accepts `authority_token` (full token) or `hermes_id` (pairing-based connect):
```python
if hermes_id:
    conn = hermes.connect_from_pairing(hermes_id)
else:
    conn = hermes.connect(authority_token)
```

**Control path rejection** — `_reject_hermes_control()` called unconditionally on `/miner/start`, `/miner/stop`, `/miner/set_mode`:
```python
# daemon.py:183-189
def _reject_hermes_control(self):
    self._send_json(403, {
        "error": "HERMES_UNAUTHORIZED",
        "message": "Hermes cannot issue control commands. "
                   "Capabilities are limited to observe and summarize."
    })
```

**Test coverage:**
- `test_pair_creates_record`
- `test_pair_is_idempotent`
- `test_connect_from_pairing`
- `test_connect_from_unknown_pairing_rejected` — `HERMES_PAIRING_NOT_FOUND`
- `test_pair_token_expires_30_days_later`
- `test_control_path_rejected` — `is_control_path()` for all three paths
- `test_observe_only_cannot_write_summary`

---

## Test Results

```
services/home-miner-daemon/tests/test_hermes.py
23 passed in 0.04s
```

---

## Decisions Made

1. **In-process adapter, not a separate service.** Avoids network hop for phase 1. The boundary is enforced in Python, not by network topology.

2. **30-day pairing token expiry.** Forwards the re-pairing trigger far enough to not annoy users, close enough to revoke a lost device within a month.

3. **`/hermes/connect` accepts `hermes_id` in body.** Enables the CLI to do pair-then-connect without the operator needing to construct a token manually.

4. **Control paths always return 403.** Simplifies enforcement — no capability lookup needed for `/miner/*`. Hermes is blocked regardless of token contents.

5. **`get_filtered_events()` has no capability gate.** Read-only listing of filtered events (already excluding sensitive content) is always permitted for active Hermes sessions.

---

## Open Tasks (Deferred)

| Task | Reason Deferred |
|------|----------------|
| Persistent Hermes sessions across daemon restart | Requires store-backed session mechanism; acceptable for milestone 1 |
| Multi-Hermes isolation (per-Hermes event visibility) | All `hermes_summary` events are currently world-readable to Hermes sessions |
| TLS/mTLS for Hermes transport | LAN-only binding for milestone 1 |
| Gateway client Agent tab with real connection state | Gateway client not yet implemented |

---

## Notes

- All error codes use `HERMES_*` prefixes matching the error taxonomy in `references/error-taxonomy.md`.
- The `user_message` filtering is implemented via `EventKind` name-based exclusion. New event kinds must be explicitly added to `HERMES_READABLE_EVENTS` to be accessible to Hermes.
- In-memory `_hermes_connections` registry in `GatewayHandler` means sessions reset on daemon restart. This is intentional for milestone 1.
- `spine.py` defines `EventKind` as a string enum. `hermes.py` imports it directly, so `HERMES_READABLE_EVENTS` contains live enum values, not string literals.
