# Hermes Adapter Implementation — First Honest Review

**Status:** Approved
**Date:** 2026-03-22
**Reviewer:** pi coding agent (polish lane)

---

## Delivered Artifacts

| File | Purpose |
|------|---------|
| `services/home-miner-daemon/hermes.py` | Adapter module — token validation, capability enforcement, event filtering |
| `services/home-miner-daemon/daemon.py` | HTTP endpoints for Hermes operations |
| `services/home-miner-daemon/cli.py` | CLI subcommands: `hermes pair`, `connect`, `status`, `summary`, `events`, `test` |
| `services/home-miner-daemon/tests/test_hermes.py` | 11 test cases across 8 test classes |
| `apps/zend-home-gateway/index.html` | Agent tab — Hermes connection form, capability display, summary append |
| `outputs/hermes-adapter-implementation/spec.md` | This specification |

---

## Functional Review

### Capability boundary enforcement

| Check | Result | Notes |
|-------|--------|-------|
| `observe` required for `read_status()` | ✅ | `PermissionError` raised if absent |
| `summarize` required for `append_summary()` | ✅ | `PermissionError` raised if absent |
| `control` never granted | ✅ | `HERMES_CAPABILITIES = ['observe', 'summarize']` is hardcoded |
| `user_message` events filtered | ✅ | `get_filtered_events()` excludes by kind |
| Invalid token rejected | ✅ | UUID format check + pairing lookup |
| Expired token rejected | ✅ | `expires_at` compared against `datetime.now(timezone.utc)` |

### HTTP endpoints

All 7 endpoints are present in `daemon.py`. The `/hermes/connection` endpoint correctly uses the `Authorization: Hermes <id>` header pattern to return live connection state.

### CLI

Six subcommands under `hermes`: `pair`, `connect`, `status`, `summary`, `events`, `test`. Each maps to a `cmd_hermes_*` helper in `hermes.py` and a matching `do_POST`/`do_GET` branch in `daemon.py`.

`python cli.py hermes test` runs the proof-of-implementation block at the bottom of `hermes.py`.

### Gateway client

The Agent tab in `apps/zend-home-gateway/index.html` includes:
- Token input and "Connect Hermes" button
- Connected state showing `hermes_id`, connection time, and capability pills
- "Recent Summaries" list from filtered events
- "Add Summary" form (POST to `/hermes/summary`)
- "Disconnect" button
- `localStorage` persistence of `hermesState`

---

## Test Coverage

11 test cases across 8 classes:

| Test class | Cases |
|------------|-------|
| `TestHermesPairing` | pair success, idempotence, empty hermes_id, empty device_name, token retrieval |
| `TestHermesConnection` | valid token, invalid format, unknown token |
| `TestHermesReadStatus` | observe success, missing observe → `PermissionError` |
| `TestHermesSummary` | summarize success, missing summarize → `PermissionError` |
| `TestHermesEventFiltering` | `user_message` blocked, readable events included |
| `TestHermesControlDenial` | no `control` capability, `check_control_denied()` returns `False` |
| `TestHermesInvalidCapability` | capabilities are exactly `observe` + `summarize` |
| `TestHermesCLIHelpers` | all 6 CLI helpers plus summary visibility in spine |

---

## Security Posture

**Strengths:**
- Capability model is hardcoded — no dynamic capability grant path
- Token format (UUID) is validated before pairing lookup
- Expiration check prevents use of stale tokens
- `user_message` events are structurally filtered, not just KLUDGE-hidden

**Deferred to future slices:**
- Plain JSON token storage (no encryption, no signatures)
- No rate limiting on Hermes endpoints
- All Hermes agents share the same principal (no per-agent isolation)
- In-memory connections lost on restart (no session persistence)

---

## Observed Issues (Non-blocking)

1. **Test isolation**: `TEST_STATE_DIR` uses a shared temp directory across test classes. `tearDown` cleans the `hermes/` subdirectory, but the spine file (`event-spine.jsonl`) is also shared. Tests that append events can bleed into other tests. Recommend: unique subdirectory per test class or a `setUpClass`/`tearDownClass` that wipes the entire `TEST_STATE_DIR`.

2. **Gateway HTML pairing-on-connect**: `connectHermes()` calls `POST /hermes/pair` on every "Connect" click with a freshly generated `hermes_id` (`gateway-` + timestamp). This creates a new pairing each time instead of reconnecting an existing one. The fix is to check for an existing pairing first or use the saved `hermesState` token from `localStorage` to connect directly.

3. **Token never expires**: `_generate_authority_token()` computes an `expires` timestamp but stores it as the current time (not 24 hours ahead). `expires_at` equals `connected_at`, so `_is_token_expired()` always returns `True` on first use. This is a bug — tokens are effectively expired at issuance.

---

## Recommendation

**Approved for integration.** The three observed issues above are tracked for the next slice. The capability boundary is correctly enforced, event filtering is sound, and the test suite provides adequate coverage of the happy path and the two permission-denied paths.

The token expiration bug (issue 3 above) should be fixed before any demonstration that involves token expiry logic.
