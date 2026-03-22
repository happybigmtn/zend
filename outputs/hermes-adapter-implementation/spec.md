# Hermes Adapter — Capability Spec

**Status:** Implemented  
**Date:** 2026-03-22  
**Lane:** `hermes-adapter-implementation`  
**Spec type:** Capability Spec (per SPEC.md guidelines)

---

## Purpose / User-Visible Outcome

Hermes is an external AI agent that monitors the Zend home miner. The Hermes
adapter is the single enforcement boundary that sits between Hermes and the
Zend event spine. After this lane lands:

- Hermes can authenticate with a 24-hour authority token and read miner status.
- Hermes can append structured summaries to the operations inbox.
- Hermes **cannot** issue control commands (start/stop/set_mode) and
  **cannot** read `user_message` events, which remain private to paired gateway
  clients.

---

## Whole-System Goal

Zend's operations inbox is derived from the append-only event spine
(`services/home-miner-daemon/spine.py`). The inbox must remain a
Hermes-readable subset of spine events. The adapter guarantees this subset
by construction: every Hermes read or write is routed through a typed
interface in `hermes.py` that enforces the capability contract.

---

## Scope (This Lane)

| Included | Not Included |
|----------|--------------|
| `HermesConnection` dataclass with `observe` / `summarize` scope | Token revocation endpoint |
| Authority token issuance and 24-hour expiration | Persistent connection state across daemon restarts |
| `read_status` — miner snapshot through adapter | Hermes `control` capability (future approval flow) |
| `append_summary` — hermes_summary events to spine | Direct inbox message access for Hermes |
| Event filtering — `user_message` excluded | Real miner hardware integration |
| `POST /hermes/pair`, `POST /hermes/connect`, `GET /hermes/status`, `POST /hermes/summary`, `GET /hermes/events` | In-memory connection table in daemon |

---

## Architecture / Runtime Contract

```
Hermes Gateway (external)
        │
        ▼
Zend Hermes Adapter  ←  hermes.py
  connect()           ←  token validation
  read_status()      ←  observe capability gate
  append_summary()   ←  summarize capability gate
  get_filtered_events()  ←  event kind filter
        │
        ▼
Event Spine  ←  spine.py (append-only JSONL journal)
```

### Data flow

1. **Pairing** — `POST /hermes/pair {hermes_id}` creates a pairing record in
   `state/hermes-pairings.json` and issues a UUID authority token valid for 24 h.
2. **Connect** — `POST /hermes/connect {authority_token}` validates the token
   and returns a `HermesConnection` (in-memory in the daemon, scoped to that
   HTTP session).
3. **Read status** — `GET /hermes/status` (with `Authorization: Hermes
   <hermes_id>`) calls `hermes.read_status(connection)` → miner simulator
   snapshot, stripped of sensitive fields.
4. **Append summary** — `POST /hermes/summary {summary_text, authority_scope}`
   calls `hermes.append_summary(connection, …)` → appends a `hermes_summary`
   event to `state/event-spine.jsonl`.
5. **Read events** — `GET /hermes/events` calls
   `hermes.get_filtered_events(connection)` → returns only
   `hermes_summary`, `miner_alert`, and `control_receipt` events; `user_message`
   is always excluded.

### Capability enforcement

| Operation | Required capability | Denied if missing |
|-----------|--------------------|--------------------|
| `read_status` | `observe` | `403 HERMES_UNAUTHORIZED` |
| `append_summary` | `summarize` | `403 HERMES_UNAUTHORIZED` |
| `GET /miner/start` | *(none — control)* | `403 HERMES_UNAUTHORIZED` |
| `GET /miner/stop` | *(none — control)* | `403 HERMES_UNAUTHORIZED` |
| `GET /miner/set_mode` | *(none — control)* | `403 HERMES_UNAUTHORIZED` |

### State files

| File | Purpose |
|------|---------|
| `state/hermes-pairings.json` | Persistent pairing records (survives daemon restart) |
| `state/hermes-tokens.json` | Authority tokens (24 h TTL) |
| `state/event-spine.jsonl` | Append-only event journal (source of truth) |

---

## Adoption Path

The Agent tab in `apps/zend-home-gateway/index.html` shows real Hermes connection
state by polling `GET /hermes/status`. The CLI in
`services/home-miner-daemon/cli.py` exposes all operations via the `hermes`
subcommand group.

---

## Acceptance Criteria

1. `POST /hermes/pair` with a new `hermes_id` creates a pairing and returns
   `{success: true, capabilities: ['observe', 'summarize']}`.
2. `POST /hermes/connect` with the issued token returns a valid
   `HermesConnection` and stores it in the daemon's connection table.
3. `GET /hermes/status` (with Hermes auth) returns a miner snapshot and HTTP
   200; without auth returns HTTP 403.
4. `POST /hermes/summary` (with Hermes auth) appends a `hermes_summary` event to
   the spine and returns `{appended: true, event_id: …}`.
5. `GET /hermes/events` never returns `user_message` events.
6. `POST /miner/start` with Hermes auth returns HTTP 403
   `HERMES_UNAUTHORIZED`.
7. `python cli.py hermes pair --hermes-id h1 --device-name "Test Hermes"`
   completes without error.
8. `python cli.py hermes summary --hermes-id h1 --text "All good"` appends an
   event and prints the event ID.

---

## Failure Handling

| Failure | Response |
|---------|----------|
| Expired token | `401 HERMES_AUTH_FAILED` with `HERMES_TOKEN_EXPIRED` message |
| Invalid token | `401 HERMES_AUTH_FAILED` with `HERMES_INVALID_TOKEN` message |
| Missing `observe` | `403 HERMES_UNAUTHORIZED` from `read_status` |
| Missing `summarize` | `403 HERMES_UNAUTHORIZED` from `append_summary` |
| Empty `summary_text` | `400 HERMES_INVALID_INPUT` |
| Unknown `hermes_id` on connect | `403 HERMES_NOT_CONNECTED` |
| Control attempt via Hermes auth | `403 HERMES_UNAUTHORIZED` |

---

## Files

### Created
- `services/home-miner-daemon/hermes.py` — adapter module
- `outputs/hermes-adapter-implementation/spec.md` — this document
- `outputs/hermes-adapter-implementation/review.md` — implementation review

### Modified
- `services/home-miner-daemon/daemon.py` — `GatewayHandler` extended with Hermes endpoints and auth header parsing
- `services/home-miner-daemon/cli.py` — `hermes` subcommand group added
- `apps/zend-home-gateway/index.html` — Agent tab polls `/hermes/status`
