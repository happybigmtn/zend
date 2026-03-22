# Hermes Adapter Implementation — Slice 001 Spec

**Lane:** `hermes-adapter-implementation`
**Slice:** 001 — First honest reviewed slice
**Status:** Implemented
**Date:** 2026-03-22

---

## Purpose

Deliver the first working implementation of the Hermes adapter: a hard capability
boundary between the Hermes AI agent and the Zend gateway. Hermes can read miner
status and append summaries to the event spine. It cannot issue control commands
or read `user_message` events. All enforcement is mechanical and verifiable.

---

## What was built

### `services/home-miner-daemon/hermes.py` (new)

The adapter module sits in-process with the daemon. It exposes four public
functions plus two auth helpers:

| Function | Description |
|---|---|
| `pair(hermes_id, device_name, validity_hours=24)` | Creates or replaces a Hermes pairing record in `state/hermes-pairing-store.json`. Returns `HermesPairing` with the raw authority token. Idempotent. |
| `connect(authority_token)` | Decodes the authority token (JSON: `hermes_id`, `principal_id`, `capabilities`, `expires_at`). Checks expiry and that all capabilities are in `['observe', 'summarize']`. Returns `HermesConnection`. |
| `read_status(connection)` | Delegates to `MinerSimulator.get_snapshot()`. Requires `observe` capability, raises `PermissionError` otherwise. |
| `append_summary(connection, summary_text, authority_scope)` | Appends a `hermes_summary` event to the event spine. Requires `summarize` capability, raises `PermissionError` otherwise. |
| `get_filtered_events(connection, limit=20)` | Loads events from the spine and returns only those in `HERMES_READABLE_EVENTS`. `user_message` is absent from this set. |
| `is_hermes_authenticated(headers)` | Parses `Authorization: Hermes <id>` header. Returns the `hermes_id` string or `None`. |
| `check_hermes_capability(hermes_id, capability)` | Looks up the stored pairing, verifies the capability is granted and the token has not expired. |

#### Constants

```python
HERMES_CAPABILITIES = ['observe', 'summarize']   # never includes 'control'
HERMES_READABLE_EVENTS = [
    EventKind.HERMES_SUMMARY,
    EventKind.MINER_ALERT,
    EventKind.CONTROL_RECEIPT,
]                                                # user_message absent
HERMES_AUTH_PREFIX = "Hermes "                   # header scheme
```

#### Token format (milestone 1 simulator)

Authority tokens are plain JSON, base64-encoded for transport:

```json
{
  "hermes_id": "hermes-001",
  "principal_id": "...",
  "capabilities": ["observe", "summarize"],
  "expires_at": "2026-03-22T12:00:00Z"
}
```

The adapter interface is designed so a future deployment can swap
`_decode_authority_token()` for a JWT verifier without changing any public API.

#### Bug fixed at implementation time

`hour` overflow: `datetime.replace(hour=now.hour + 24)` raises `ValueError`
when `now.hour >= 0`. Fixed by using `datetime + timedelta(hours=validity_hours)`.

---

### `services/home-miner-daemon/daemon.py` (modified)

`GatewayHandler` routes five new endpoints:

| Method | Path | Auth | Description |
|---|---|---|---|
| POST | `/hermes/pair` | None | Create/replace Hermes pairing |
| POST | `/hermes/connect` | None | Validate authority token, return connection |
| GET | `/hermes/status` | `Authorization: Hermes <id>` | Read miner status |
| POST | `/hermes/summary` | `Authorization: Hermes <id>` | Append summary to spine |
| GET | `/hermes/events` | `Authorization: Hermes <id>` | Read filtered events |

The three pre-existing control endpoints — `/miner/start`, `/miner/stop`,
`/miner/set_mode` — now check for Hermes auth before processing and return
HTTP 403 with `HERMES_UNAUTHORIZED` if Hermes attempts a control command.
This is the enforcement point for the capability boundary.

---

### `services/home-miner-daemon/cli.py` (modified)

Five new subcommands under the `hermes` top-level command:

```
python3 cli.py hermes pair    --hermes-id ID --device-name NAME
python3 cli.py hermes connect --token TOKEN
python3 cli.py hermes status  --hermes-id ID
python3 cli.py hermes summary --hermes-id ID --text TEXT [--scope observe]
python3 cli.py hermes events  --hermes-id ID [--limit 20]
```

---

## Boundaries enforced

| Boundary | Mechanism | Evidence |
|---|---|---|
| Hermes cannot read `user_message` | `HERMES_READABLE_EVENTS` excludes it | T7 |
| Hermes cannot issue control commands | `_reject_hermes_control()` → 403 on control paths | T8 |
| Token must not be expired | `_decode_authority_token()` checks `expires_at` | T8 (bad token) |
| Capability must be granted | `check_hermes_capability()` verifies stored record | T2, T3, T4 |
| `observe` required to read status | `read_status()` raises `PermissionError` | T3 |
| `summarize` required to append summary | `append_summary()` raises `PermissionError` | T4 |

---

## Validation evidence

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

---

## What was NOT done in this slice

- **`tests/test_hermes.py`** — eight unit tests are pending. Integration proof
  covers happy paths and the two critical boundary rejections. Unit tests for
  individual function behavior (expired token, malformed JSON, missing fields)
  are not yet written.
- **Agent tab update** — `apps/zend-home-gateway/index.html` still shows
  "Hermes not connected". Planned for a future slice.
- **Structured log events** — events like `gateway.hermes.summary_appended`
  and `gateway.hermes.unauthorized` per `references/observability.md` are not
  yet wired. Depends on plan 007.

---

## Remaining tasks

- [ ] Write `tests/test_hermes.py` with eight unit tests covering individual
        function behaviors
- [ ] Update gateway Agent tab with real Hermes connection state
- [ ] Add structured log events per `references/observability.md`
