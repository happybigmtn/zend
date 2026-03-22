# Hermes Adapter Implementation — Review

**Lane:** `hermes-adapter-implementation`
**Date:** 2026-03-22
**Status:** Ready for integration
**Test results:** 22/22 passing

---

## What was built

### `services/home-miner-daemon/hermes.py` — Adapter module

The entire capability boundary lives here. Key elements:

- **Capability constants**: `HERMES_CAPABILITIES = ['observe', 'summarize']` — `control` is never included
- **`HermesConnection` dataclass**: carries `hermes_id`, `principal_id`, `capabilities`, `connected_at`, `device_name`; `has_capability()` method for runtime checks
- **`connect()`**: Parses base64-JWT authority token; validates required fields, expiration, capability presence; **rejects** `control` in token; auto-pairs if pairing missing
- **`read_status()`**: Enforces `observe`; delegates to `daemon.miner.get_snapshot()`
- **`append_summary()`**: Enforces `summarize`; appends `EventKind.HERMES_SUMMARY` to spine
- **`get_filtered_events()`**: Over-fetches 3× to account for filtering; excludes `user_message` events; returns only `hermes_summary`, `miner_alert`, `control_receipt`
- **`is_hermes_auth_header()` / `extract_hermes_id()`**: Auth header utilities used by daemon and CLI

### `services/home-miner-daemon/daemon.py` — HTTP endpoints

Five handlers added to `GatewayHandler`:

| Handler | Method | Description |
|---------|--------|-------------|
| `_handle_hermes_pair` | `POST /hermes/pair` | Create Hermes pairing |
| `_handle_hermes_connect` | `POST /hermes/connect` | Establish connection with authority token |
| `_handle_hermes_status` | `GET /hermes/status` | Read miner status (adapter-gated) |
| `_handle_hermes_summary` | `POST /hermes/summary` | Append summary to spine (adapter-gated) |
| `_handle_hermes_events` | `GET /hermes/events` | Read filtered events |

`_is_hermes_request()` + `_get_hermes_connection()` extract and validate Hermes auth. All `/miner/*` control commands return `403 HERMES_UNAUTHORIZED` when called with Hermes auth.

### `services/home-miner-daemon/cli.py` — CLI subcommands

Five subcommands under `hermes`:

```
hermes pair     --hermes-id [--device-name]
hermes connect  --hermes-id
hermes status   --hermes-id
hermes summary  --hermes-id --text [--scope]
hermes events   --hermes-id [--limit]
```

**Bug fixed during review:** The file had a duplicate `daemon_call` function — the first lacked `headers` support, the second (correct) version appeared later. The first definition was removed.

### `services/home-miner-daemon/tests/test_hermes.py` — 22 unit tests

| Test class | Coverage |
|-----------|---------|
| `TestHermesConstants` | Capabilities and readable-event constants |
| `TestHermesAuthHeader` | `is_hermes_auth_header`, `extract_hermes_id` |
| `TestHermesConnect` | Valid/expired/malformed/missing-field tokens; control-capability rejection |
| `TestHermesReadStatus` | Observe enforcement; observe bypass |
| `TestHermesAppendSummary` | Summarize enforcement; event creation; spine verification |
| `TestHermesEventFiltering` | `user_message` blocked; `miner_alert` allowed; `control_receipt` allowed |
| `TestHermesPairing` | Idempotency; capability assignment |
| `TestHermesCapabilityBoundary` | `has_capability()` method |

---

## Security analysis

### Capability enforcement ✓

`observe` is required for `read_status`. `summarize` is required for `append_summary`. Both are enforced at the adapter layer with `HermesUnauthorizedError`.

### Control never granted ✓

`connect()` explicitly checks for `control` in the token's capabilities and raises `HermesUnauthorizedError` if present. The daemon additionally returns `403 HERMES_UNAUTHORIZED` for any `/miner/*` request with Hermes auth.

### Event filtering ✓

`get_filtered_events()` builds `HERMES_READABLE_EVENTS` from the enum and filters the event stream. `user_message` is not in the list and is never returned.

### Token validation ✓

Expired tokens → `HermesTokenExpiredError`. Malformed JSON → `HermesInvalidTokenError`. Missing fields → `HermesInvalidTokenError`. All covered by tests.

---

## Design decisions

1. **In-process adapter**: The adapter runs in the same process as the daemon. This is intentional — the boundary is capability-scoped, not deployment-scoped.
2. **Simplified authority token**: Milestone 1 uses base64-encoded JSON with an `expires_at` ISO timestamp. Production should use proper JWT with cryptographic verification.
3. **Idempotent pairing**: Re-pairing with the same `hermes_id` returns the existing pairing record without creating duplicates.
4. **Auto-pairing on connect**: If Hermes connects without pairing first, `connect()` auto-creates a pairing with `observe` + `summarize`. This is convenient for development.

---

## Known issues

1. **File-path resolution at import time**: `store.py` and `spine.py` resolve `STATE_DIR` at module-import time. Tests work around this by setting `ZEND_STATE_DIR` to a unique temp directory per test class, but a future refactor should make this lazy.

---

## Open tasks

- [x] Create `hermes.py` adapter module
- [x] Implement `HermesConnection` with authority token validation
- [x] Implement `read_status` through adapter
- [x] Implement `append_summary` through adapter
- [x] Implement event filtering (block `user_message` events)
- [x] Add Hermes pairing endpoint to daemon
- [x] Add Hermes CLI subcommands
- [x] Write unit tests for adapter boundary enforcement (22 tests)
- [ ] Gateway client Agent tab polling `/hermes/status`
- [ ] End-to-end integration test (pair → connect → read status → append summary → verify in spine)

---

## Conclusion

The Hermes adapter implementation is complete and verified. All core security properties hold:

- Hermes can observe miner status ✓
- Hermes can append summaries to the event spine ✓
- Hermes **cannot** issue control commands (403 blocked) ✓
- Hermes **cannot** read `user_message` events (filtered) ✓
- Invalid/expired tokens are rejected ✓
- `control` capability in a token triggers rejection ✓
- All 22 unit tests pass ✓

The implementation is ready for integration testing.
