# Hermes Adapter — Implementation Spec

**Status:** Implemented (4 blockers pending)
**Lane:** `hermes-adapter-implementation`
**Source root:** `services/home-miner-daemon/`
**Reviewed:** 2026-03-22

---

## What Was Built

A capability-scoped adapter boundary for Hermes AI agents connecting to the Zend
home-miner daemon. Hermes agents are restricted to two capabilities — `observe` and
`summarize` — and can never issue miner control commands or read user messages.

The adapter is implemented as a pure Python module (`hermes.py`) that mediates every
Hermes interaction with the system. All enforcement happens at three independent
layers: token parse time, adapter function level, and HTTP handler level.

---

## Repo Layout

```
services/home-miner-daemon/
├── hermes.py          # Core adapter (here be the boundary)
├── daemon.py          # HTTP server; wires hermes.py into endpoints
├── cli.py             # CLI commands: hermes pair/status/summary/events
├── spine.py           # Append-only event journal (event source of truth)
├── store.py           # Principal + gateway pairing store
└── tests/
    └── test_hermes.py  # 20 unit tests (all passing)
```

**State files written by this module:**

| File | Purpose |
|---|---|
| `state/hermes-pairings.json` | Hermes agent pairing records (separate from gateway store) |
| `state/principal.json` | Shared principal identity |

Note: `state/principal.json` is shared with `store.py`. See B4 in review.md.

---

## Adapter Contract

### `hermes.connect(authority_token: str) -> HermesConnection`

Parses a base64-encoded JSON authority token, validates expiration, checks that all
capabilities are in the Hermes allowlist (`observe`, `summarize`), and returns a live
`HermesConnection`. Raises `ValueError` on any validation failure.

Token schema:
```json
{
  "hermes_id": "string",
  "principal_id": "string",
  "capabilities": ["observe", "summarize"],
  "expires_at": "2026-03-23T00:00:00+00:00"
}
```

### `hermes.pair_hermes(hermes_id: str, device_name: str) -> HermesPairing`

Idempotent. Creates or refreshes a Hermes pairing record in
`state/hermes-pairings.json`. Issues a UUID pairing token. The daemon HTTP layer
(`/hermes/pair`) then generates an authority token from the pairing record.

### `hermes.read_status(connection: HermesConnection) -> dict`

Requires `observe` capability. Returns a subset of `miner.get_snapshot()` with
sensitive internal fields stripped. Raises `PermissionError` without `observe`.

### `hermes.append_summary(connection: HermesConnection, summary_text: str,
authority_scope: str) -> dict`

Requires `summarize` capability. Appends a `hermes_summary` event to the event spine
via `spine.append_hermes_summary()`. Raises `PermissionError` without `summarize`.

### `hermes.get_filtered_events(connection: HermesConnection, limit: int) -> list`

Returns events from the spine filtered to `HERMES_READABLE_EVENTS`:
`['hermes_summary', 'miner_alert', 'control_receipt']`. `user_message` is
explicitly excluded. Also strips sensitive payload fields from `control_receipt`
events via `_strip_sensitive_fields()`.

### `hermes.generate_authority_token(...) -> str`

Helper that produces a base64-encoded authority token. Used by the pairing flow
and by tests. Not a security boundary in M1 (see S1 in review.md).

---

## HTTP Endpoints Added to daemon.py

| Method | Path | Auth | Description |
|---|---|---|---|
| POST | `/hermes/pair` | None (LAN-only M1) | Create/refresh Hermes pairing |
| POST | `/hermes/connect` | `authority_token` body field | Connect with authority token |
| GET | `/hermes/status` | `Authorization: Hermes <hermes_id>` | Read miner status via adapter |
| POST | `/hermes/summary` | `Authorization: Hermes <hermes_id>` | Append Hermes summary |
| GET | `/hermes/events` | `Authorization: Hermes <hermes_id>` | Get filtered event list |
| POST | `/miner/start` | No Hermes prefix | Control: miner start (blocked for Hermes) |
| POST | `/miner/stop` | No Hermes prefix | Control: miner stop (blocked for Hermes) |
| POST | `/miner/set_mode` | No Hermes prefix | Control: set mode (blocked for Hermes) |

---

## CLI Commands (cli.py)

```
python -m daemon.cli hermes pair    --hermes-id <id> [--device <name>]
python -m daemon.cli hermes status --hermes-id <id>
python -m daemon.cli hermes summary --hermes-id <id> --text <text> [--scope <scope>]
python -m daemon.cli hermes events --hermes-id <id> [--limit <n>]
```

---

## Enforcement Layers

**Layer 1 — Token parse** (`_parse_token` in hermes.py):
Rejects tokens containing unknown capabilities (e.g., `control`) at parse time.
This fires on every `connect()` call.

**Layer 2 — Adapter functions** (`read_status`, `append_summary`, `get_filtered_events`):
Each function checks `connection.capabilities` before performing the operation.
`PermissionError` is raised without the required capability.

**Layer 3 — HTTP handlers** (`_handle_control_check` in daemon.py):
Every control endpoint (`/miner/start`, `/miner/stop`, `/miner/set_mode`) runs
`_handle_control_check()` which looks for the `Authorization: Hermes <id>` prefix.
If found, returns HTTP 403 and never calls the miner. This is independent of
the token system — two separate barriers.

---

## Test Results

```
services/home-miner-daemon/tests/test_hermes.py
20 tests, all passing
```

Coverage map:
- `HERMES_CAPABILITIES` definitions
- `HERMES_READABLE_EVENTS` exclusions
- Token generation and `connect()` validation
- `read_status` requires `observe`
- `append_summary` requires `summarize`
- `user_message` filtered from event list
- `miner_alert` allowed through filter
- `control` rejected at token-parse level
- Pairing idempotence

---

## Blocking Issues (must fix before merge)

| ID | File | Line | Description |
|---|---|---|---|
| B1 | daemon.py | 196-204 | Control endpoints call miner method twice per request |
| B2 | daemon.py | 170-176, 299-310 | Duplicate `do_GET` — first definition is dead code |
| B3 | hermes.py | 215, 229 | `token_expires_at` set to `datetime.now()` (current time) — tokens expire instantly |
| B4 | hermes.py | 238-249 | `_get_or_create_principal_id` creates unpersisted random UUID; diverges from `store.py`'s `load_or_create_principal()` |

See `review.md` for full detail, evidence, and recommended fixes.

---

## Security Posture (M1 — LAN-only)

The trust boundary for M1 is the local network. The following are **known acceptable
gaps** for LAN-only M1 but are **hard blockers** before any network exposure:

- Authority token validated on connect but not bound to subsequent requests (S1)
- No authentication on `/hermes/pair` (S5)
- JSON store writes are not atomic; concurrent pairings could lose writes (S5)

---

## Milestone Fit

The implementation satisfies 7 of 8 product spec requirements for the Hermes
adapter boundary layer:

- ✅ Hermes connects through Zend adapter, never directly
- ✅ Observe-only + summary-append in phase 1
- ✅ Direct miner control through Hermes deferred
- ✅ Hermes receives only explicitly granted capabilities
- ✅ Event spine is source of truth
- ✅ Hermes cannot read `user_message` events
- ✅ Pairing endpoint exists
- ⚠️ Agent boundary (no authority without explicit grant): partial — token is ceremonial (S1)
