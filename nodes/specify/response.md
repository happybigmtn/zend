
All components verified. Let me provide the final summary:

---

## Summary: Hermes Adapter Implementation — Slice 1

### What was built

**`services/home-miner-daemon/hermes.py`** (614 lines)
- `HermesConnection`, `HermesPairing`, `HermesAuthorityToken` data classes
- `pair_hermes()` — idempotent Hermes pairing
- `issue_authority_token()` / `validate_authority_token()` — token lifecycle
- `connect(authority_token)` — establishes session from valid token
- `read_status(connection, miner_snapshot_fn)` — requires `observe` capability
- `append_summary(connection, summary_text, authority_scope)` — requires `summarize` capability
- `get_filtered_events(connection, limit)` — blocks `user_message` events
- `HermesReadableEvent` enum defining allowed event kinds
- `HermesPermissionError` with machine-readable error codes

**`services/home-miner-daemon/daemon.py`** (487 lines, delta ~200 lines)
- `POST /hermes/pair` — creates pairing + issues token
- `POST /hermes/connect` — validates token, returns connection state
- `GET /hermes/status` — read miner status (observe)
- `POST /hermes/summary` — append summary to spine (summarize)
- `GET /hermes/events` — filtered event read (no user_message)
- `GET /hermes/connection` — current connection state
- Control endpoint hardening: Hermes auth returns `403 HERMES_UNAUTHORIZED` on `/miner/*`

**`services/home-miner-daemon/cli.py`** (495 lines, delta ~120 lines)
- `zend hermes pair --hermes-id [--device-name]`
- `zend hermes connect --hermes-id [--token] [--status]`
- `zend hermes summary --hermes-id [--token] --text [--scope]`
- `zend hermes events --hermes-id [--token]`
- Token persistence in `state/hermes-token-<hermes_id>.json`

### Verification results

| Test | Result |
|---|---|
| Module syntax check (py_compile) | ✅ hermes.py, daemon.py, cli.py |
| Module proof-of-concept (`python3 hermes.py`) | ✅ |
| 10 in-process integration tests | ✅ All pass |
| 6 daemon endpoint tests (live server) | ✅ All pass |
| Control rejection (Hermes on `/miner/start`) | ✅ 403 HERMES_UNAUTHORIZED |
| User message event filtering | ✅ Not leaked |
| CLI hermes pair command | ✅ |
| End-to-end smoke | ✅ |

### Durable artifacts

- **`outputs/hermes-adapter-implementation/spec.md`** — specification with test results, verification commands, design decisions, and remaining work
- **`outputs/hermes-adapter-implementation/review.md`** — honest review with issues found, watch items, and recommendations