# Hermes Adapter — Capability Spec

**Status:** Implemented
**Date:** 2026-03-22
**Lane:** `hermes-adapter-implementation`
**Files produced:** `services/home-miner-daemon/hermes.py`, `services/home-miner-daemon/daemon.py`, `services/home-miner-daemon/cli.py`, `services/home-miner-daemon/tests/test_hermes.py`

---

## Purpose / User-Visible Outcome

An external Hermes agent can read miner status and append summaries to the event spine through the Zend daemon, but cannot read user messages or issue control commands. The boundary is enforced in-process by the daemon — no separate service, no network hop.

---

## Whole-System Goal

Hermes is a monitoring/analysis agent that observes miner state and generates natural-language summaries. It must be firewalled from:
- **Control** — cannot start, stop, or change miner mode
- **User content** — cannot read `user_message` events
- **Pairing events** — cannot read `pairing_requested` or `pairing_granted`

---

## Scope

This lane delivers the adapter module, daemon endpoints, CLI commands, and unit tests for milestone 1 of the Hermes integration.

---

## Architecture

```
Hermes Gateway
      |
      v
services/home-miner-daemon/hermes.py   ← capability boundary
      |
      v
spine.py (event-spine.jsonl)  ← append-only journal
```

The adapter is a Python module (`hermes.py`) imported in-process by `daemon.py`. It is a **capability boundary**, not a deployment boundary.

---

## Runtime Contract

### `HermesConnection` dataclass

```python
@dataclass
class HermesConnection:
    hermes_id: str
    principal_id: str
    capabilities: List[str]   # subset of ['observe', 'summarize']
    connected_at: str         # ISO 8601
```

### `connect(authority_token: str) → HermesConnection`

Parses a compact JSON authority token and returns a live connection.

**Token schema:**
```json
{
  "hermes_id": "string",
  "principal_id": "string",
  "capabilities": ["observe", "summarize"],
  "expires_at": "2026-04-21T00:00:00Z"
}
```

**Error codes raised:**

| Condition | Exception | Error prefix |
|-----------|-----------|-------------|
| Malformed JSON | `ValueError` | `HERMES_AUTH_INVALID` |
| Missing `hermes_id` or `principal_id` | `ValueError` | `HERMES_AUTH_INVALID` |
| `capabilities` not a list | `ValueError` | `HERMES_AUTH_INVALID` |
| Expired token | `PermissionError` | `HERMES_TOKEN_EXPIRED` |
| `control` or unknown capability | `PermissionError` | `HERMES_UNAUTHORIZED_CAPABILITY` |
| No Hermes capabilities granted | `PermissionError` | `HERMES_UNAUTHORIZED` |

### `connect_from_pairing(hermes_id: str) → HermesConnection`

Connects using a previously stored pairing record from `state/hermes-pairing-store.json`. Raises `HERMES_PAIRING_NOT_FOUND` if no record exists.

### `pair_hermes(hermes_id: str, device_name: str) → dict`

Creates or updates a Hermes pairing record (idempotent). Capabilities are always `['observe', 'summarize']`. Token expires 30 days from creation. Pairing is stored in `state/hermes-pairing-store.json`.

### `read_status(connection: HermesConnection) → dict`

Delegates to `daemon.miner.get_snapshot()`. Requires `'observe'` in `connection.capabilities`. Raises `PermissionError` with `HERMES_UNAUTHORIZED` if missing.

### `append_summary(connection, summary_text, authority_scope=None) → dict`

Appends a `hermes_summary` event to `event-spine.jsonl`. Requires `'summarize'`. Validates non-empty text. Returns:
```json
{
  "appended": true,
  "event_id": "uuid",
  "kind": "hermes_summary",
  "created_at": "2026-03-22T..."
}
```

### `get_filtered_events(connection, limit=20) → List[dict]`

Returns the most recent `limit` events from the spine, filtered to:

| Allowed | Excluded |
|---------|----------|
| `hermes_summary` | `user_message` |
| `miner_alert` | `pairing_requested` |
| `control_receipt` | `pairing_granted` |
| | `capability_revoked` |

No capability is required to read (read-only listing is always permitted for active sessions).

---

## Constants

```python
HERMES_CAPABILITIES = ['observe', 'summarize']
HERMES_READABLE_EVENTS = [HERMES_SUMMARY, MINER_ALERT, CONTROL_RECEIPT]
HERMES_WRITABLE_EVENTS = [HERMES_SUMMARY]
CONTROL_PATHS = ['/miner/start', '/miner/stop', '/miner/set_mode']
```

---

## Daemon HTTP Endpoints

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| `POST` | `/hermes/connect` | body `authority_token` or `hermes_id` | Establish Hermes session |
| `POST` | `/hermes/pair` | — | Create/update Hermes pairing |
| `GET` | `/hermes/status` | `Authorization: Hermes <id>` | Read miner status (observe gate) |
| `POST` | `/hermes/summary` | `Authorization: Hermes <id>` | Append summary (summarize gate) |
| `GET` | `/hermes/events` | `Authorization: Hermes <id>` | Read filtered events |
| `POST` | `/miner/start` | — | Always 403 for Hermes |
| `POST` | `/miner/stop` | — | Always 403 for Hermes |
| `POST` | `/miner/set_mode` | — | Always 403 for Hermes |

Control paths (`/miner/*`) return HTTP 403 unconditionally for Hermes — no capability lookup needed. The daemon checks the `Authorization` header on all `/hermes/*` paths and uses `hermes.is_control_path()` for control paths.

---

## CLI Subcommands

```
python3 cli.py hermes pair    --hermes-id <id> [--device-name <name>]
python3 cli.py hermes connect --hermes-id <id> [--device-name <name>] [--token <token>]
python3 cli.py hermes status  --hermes-id <id>
python3 cli.py hermes summary --hermes-id <id> --text <text> [--scope <csv>]
python3 cli.py hermes events  --hermes-id <id>
```

The `hermes connect` command without `--token` performs an inline pair-then-connect using the daemon's pairing store (no token construction needed in the CLI).

---

## Boundaries Enforced

| Boundary | Mechanism |
|----------|-----------|
| No `control` capability | `connect()` raises `HERMES_UNAUTHORIZED_CAPABILITY` |
| Control path rejection | `daemon.py` `_reject_hermes_control()` always returns 403 |
| `user_message` filtering | `get_filtered_events()` uses `EventKind` name set |
| Capability-gated reads | `read_status()` checks `'observe'` |
| Capability-gated writes | `append_summary()` checks `'summarize'` |
| Token expiration | `connect()` checks `expires_at` |

---

## Files

| File | Role |
|------|------|
| `services/home-miner-daemon/hermes.py` | Adapter module (305 lines) |
| `services/home-miner-daemon/daemon.py` | `GatewayHandler` with Hermes endpoints added |
| `services/home-miner-daemon/spine.py` | `EventKind` enum, event journal (shared) |
| `services/home-miner-daemon/store.py` | Principal/pairing store (shared) |
| `services/home-miner-daemon/cli.py` | Hermes CLI subcommands |
| `services/home-miner-daemon/tests/test_hermes.py` | 23 unit tests |
| `services/home-miner-daemon/state/hermes-pairing-store.json` | Pairing records (runtime, gitignored) |

---

## Acceptance Criteria

- [ ] `hermes.connect()` rejects tokens with `control` capability
- [ ] `hermes.read_status()` raises `PermissionError` without `observe`
- [ ] `hermes.append_summary()` raises `PermissionError` without `summarize`
- [ ] `hermes.append_summary()` raises `ValueError` for empty/whitespace text
- [ ] `hermes.get_filtered_events()` excludes `user_message`
- [ ] `/miner/*` returns 403 for Hermes regardless of token contents
- [ ] `pair_hermes()` is idempotent
- [ ] Pairing tokens expire 30 days after creation
- [ ] All 23 tests pass

---

## Non-Goals

- Persistent Hermes sessions across daemon restart (in-memory `_hermes_connections`)
- Hermes reading `capability_revoked` events
- Multi-Hermes isolation (any paired Hermes can read any `hermes_summary`)
- TLS or mTLS for Hermes-to-daemon transport (LAN-only binding for milestone 1)

---

## Design Decisions

1. **In-process adapter, not a separate service.** A deployment boundary would add network hop complexity for phase 1. The capability boundary is enforced in Python code.

2. **30-day pairing token expiry.** Long enough for normal operation; short enough to force re-pairing if a Hermes device is lost.

3. **`/hermes/connect` accepts `hermes_id` in body** (in addition to authority token). Enables CLI convenience — pair-then-connect without token construction.

4. **Control paths always return 403 for Hermes.** Simplifies the enforcement: no capability lookup needed for `/miner/*`; Hermes is blocked regardless of what token it presents.

5. **`get_filtered_events()` is capability-gated read (no gate).** Any active Hermes session can list events; this is acceptable since the filter already excludes sensitive content.
