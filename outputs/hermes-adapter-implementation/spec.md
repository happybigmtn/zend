# Hermes Adapter Implementation — Slice Spec

**Status:** Implemented
**Slice:** 001 — First honest reviewed slice
**Date:** 2026-03-22
**Frontier:** `hermes-adapter-implementation`

## Purpose

This slice delivers the first working implementation of the Hermes adapter: a
capability boundary between the Hermes AI agent and the Zend gateway contract.
Hermes can read miner status and append summaries to the event spine, but cannot
issue control commands or read user messages.

## What was built

### New file: `services/home-miner-daemon/hermes.py`

The adapter module implements four public functions:

- **`pair(hermes_id, device_name, validity_hours=24)`**
  Creates or replaces a Hermes pairing record in `state/hermes-pairing-store.json`
  and returns a `HermesPairing` with the raw authority token. Idempotent.

- **`connect(authority_token)`**
  Decodes the authority token (JSON: `hermes_id`, `principal_id`,
  `capabilities`, `expires_at`), checks it has not expired, and that all
  capabilities are in `['observe', 'summarize']`. Raises `ValueError` on any
  violation. Returns a `HermesConnection` dataclass.

- **`read_status(connection)`**
  Delegates to `MinerSimulator.get_snapshot()`. Requires `observe` capability,
  raises `PermissionError` otherwise.

- **`append_summary(connection, summary_text, authority_scope)`**
  Appends a `hermes_summary` event to the event spine via `spine.append_event`.
  Requires `summarize` capability, raises `PermissionError` otherwise.

- **`get_filtered_events(connection, limit=20)`**
  Loads events from the spine, filters out anything not in
  `HERMES_READABLE_EVENTS = [HERMES_SUMMARY, MINER_ALERT, CONTROL_RECEIPT]`,
  then returns the most recent `limit` items. This is how the user_message
  blocking is enforced — `user_message` is simply absent from the readable set.

- **`is_hermes_authenticated(headers)`**
  Parses the `Authorization: Hermes <id>` header. Returns the `hermes_id` string
  or `None`.

- **`check_hermes_capability(hermes_id, capability)`**
  Looks up the pairing record, verifies the capability is granted, and checks
  the token has not expired.

### Constants

```python
HERMES_CAPABILITIES = ['observe', 'summarize']   # never includes 'control'
HERMES_READABLE_EVENTS = [HERMES_SUMMARY, MINER_ALERT, CONTROL_RECEIPT]
HERMES_AUTH_PREFIX = "Hermes "                   # header scheme
```

### New file: `state/hermes-pairing-store.json`

Created alongside the existing device pairing store. Format:

```json
{
  "hermes-001": {
    "hermes_id": "hermes-001",
    "principal_id": "...",
    "device_name": "hermes-agent",
    "capabilities": ["observe", "summarize"],
    "paired_at": "2026-03-22T23:03:56+00:00",
    "token": "{...authority token JSON...}",
    "token_expires_at": "2026-03-23T23:03:56+00:00"
  }
}
```

### Modified: `services/home-miner-daemon/daemon.py`

`GatewayHandler` now routes five new endpoints:

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | `/hermes/pair` | None | Create/replace Hermes pairing |
| POST | `/hermes/connect` | None | Validate authority token, return connection |
| GET | `/hermes/status` | `Authorization: Hermes <id>` | Read miner status |
| POST | `/hermes/summary` | `Authorization: Hermes <id>` | Append summary to spine |
| GET | `/hermes/events` | `Authorization: Hermes <id>` | Read filtered events |

Additionally, the pre-existing `/miner/start`, `/miner/stop`, and
`/miner/set_mode` endpoints now check for Hermes auth before processing and
return HTTP 403 with `HERMES_UNAUTHORIZED` if Hermes tries to issue a control
command. This is the enforcement point for the capability boundary.

### Modified: `services/home-miner-daemon/cli.py`

Five new subcommands under the `hermes` top-level command:

```
python3 cli.py hermes pair    --hermes-id ID --device-name NAME
python3 cli.py hermes connect --token TOKEN
python3 cli.py hermes status  --hermes-id ID
python3 cli.py hermes summary --hermes-id ID --text TEXT [--scope observe]
python3 cli.py hermes events  --hermes-id ID [--limit 20]
```

## Boundaries enforced

| Boundary | Mechanism | Tested |
|----------|-----------|--------|
| Hermes cannot read `user_message` | `HERMES_READABLE_EVENTS` excludes `user_message` | T7 |
| Hermes cannot issue control commands | `_reject_hermes_control()` returns 403 on control paths | T8 |
| Token must not be expired | `_decode_authority_token()` checks `expires_at` | T8 (bad token) |
| Capability must be granted | `check_hermes_capability()` verifies stored record | T2, T3, T4 |
| `observe` required to read status | `read_status()` checks `connection.capabilities` | T3 |
| `summarize` required to append | `append_summary()` checks `connection.capabilities` | T4 |

## Validation results

All eight integration checks pass:

```
T1  Pair Hermes                           → 200, capabilities: [observe, summarize]
T2  Status without Hermes auth            → 401 HERMES_UNAUTHENTICATED
T3  Status with Hermes auth               → 200, miner snapshot returned
T4  Append summary                        → 200, appended: true
T5  Read filtered events                  → 200, [hermes_summary] only
T6  Inject user_message to spine          → event appended
T7  Re-read events after user_message     → user_message absent ✓
T8  Control attempt from Hermes           → 403 HERMES_UNAUTHORIZED ✓
```

## What was NOT done in this slice

- **Agent tab update** — `apps/zend-home-gateway/index.html` still shows
  "Hermes not connected". Planned for a future slice.
- **Formal tests** — `test_hermes.py` is pending.
- **Observability logging** — structured log events for Hermes actions are
  pending (depends on plan 007).

## Remaining tasks

- [ ] Write `tests/test_hermes.py` with 8 unit tests
- [ ] Update gateway client Agent tab with real connection state
- [ ] Add structured log events per `references/observability.md`
