# Hermes Adapter — Capability Spec

**Status:** Implemented (Milestone 1)
**Artifact:** `outputs/hermes-adapter-implementation/spec.md`
**Last Updated:** 2026-03-22

---

## Purpose / User-Visible Outcome

A Hermes AI agent connected to the Zend home-miner gateway can observe miner status and append summaries to the event spine, but cannot send control commands, mutate payout targets, or read user messages. The boundary is enforced by a Zend-native adapter module that runs in-process with the daemon.

After this capability lands, a Hermes agent with a valid authority token can:
- Authenticate to the daemon via `POST /hermes/connect`
- Read live miner status via `GET /hermes/status`
- Append structured summaries via `POST /hermes/summary`
- Read filtered event history via `GET /hermes/events`

---

## Whole-System Goal

Keep the Zend gateway contract Hermes-agnostic. The adapter is a thin, auditable enforcement layer that translates Hermes capability requests into gateway operations. This prevents Hermes from becoming an implicit control plane and preserves the product boundary defined in `references/hermes-adapter.md`.

---

## Scope

### In Scope

- Authority token validation (principal_id, hermes_id, expiration)
- Capability-gated adapter operations: `read_status`, `append_summary`
- Event filtering that excludes `user_message` from Hermes reads
- Hermes pairing endpoint (`POST /hermes/pair`) integrated into the daemon HTTP server
- Connection registry so authenticated Hermes sessions are tracked in-memory

### Out of Scope

- JWT signing or asymmetric token validation (Milestone 2)
- Hermes control capability (`control` scope — not in Milestone 1)
- Inbox message composition or user_message read access
- Payout target mutation
- Hermes-to-Hermes federation

---

## Architecture / Runtime Contract

### Module Location

`services/home-miner-daemon/hermes.py` — a pure Python module with no external dependencies beyond the daemon's own `spine` and `store` libraries.

### Key Data Structures

**`HermesConnection`** — a live session record produced by `connect()`:
```python
hermes_id:       str          # Hermes agent identity
principal_id:    str          # Zend principal the Hermes is acting on behalf of
capabilities:    List[str]    # granted scope, e.g. ['observe', 'summarize']
connected_at:    str          # ISO-8601 UTC timestamp
```

**`HermesPairing`** — a durable pairing record stored in `state/pairing-store.json` under the `_hermes` key:
```python
hermes_id, principal_id, device_name, capabilities, paired_at, token_expires_at
```

### Adapter Operations

| Function | Capability Required | Effect |
|---|---|---|
| `read_status(conn)` | `observe` | Returns `MinerSimulator.get_snapshot()` — status, mode, hashrate, temperature, uptime |
| `append_summary(conn, text, scope)` | `summarize` | Appends `hermes_summary` event to the event spine |
| `get_filtered_events(conn, limit)` | `observe` | Returns last N events filtered to readable kinds; **blocks `user_message`** |

### Event Kind Access Matrix

| EventKind | Readable by Hermes | Writable by Hermes |
|---|---|---|
| `HERMES_SUMMARY` | ✅ | ✅ |
| `MINER_ALERT` | ✅ | ❌ |
| `CONTROL_RECEIPT` | ✅ | ❌ |
| `USER_MESSAGE` | **blocked** | ❌ |
| `PAIRING_GRANTED` | ❌ | ❌ |
| `PAIRING_REQUESTED` | ❌ | ❌ |
| `CAPABILITY_REVOKED` | ❌ | ❌ |

### Daemon HTTP Endpoints

| Method | Path | Auth | Description |
|---|---|---|---|
| `POST` | `/hermes/pair` | none | Create Hermes pairing record, auto-connect |
| `POST` | `/hermes/connect` | header `Authorization: Hermes <hermes_id>` | Validate token, establish connection |
| `GET` | `/hermes/status` | Hermes connection in registry | `read_status` via adapter |
| `GET` | `/hermes/events` | Hermes connection in registry | `get_filtered_events` via adapter |
| `POST` | `/hermes/summary` | Hermes connection in registry | `append_summary` via adapter |
| `GET` | `/hermes/connect` | header `Authorization: Hermes <hermes_id>` | Return connection state |

### Token Expiry

Default expiry is 30 days from pairing. `_is_token_expired()` performs a timezone-aware UTC comparison against `datetime.now(timezone.utc)`.

---

## Adoption Path

The adapter is loaded by `daemon.py` at startup via `import hermes`. No separate service process is required for Milestone 1; the in-process design reflects that the boundary is a capability scope rather than a deployment boundary.

A future migration to a separate Hermes-adapter service would preserve the same public interface.

---

## Acceptance Criteria

1. `hermes.pair_hermes(hermes_id, device_name)` creates a record in `state/pairing-store.json` under `_hermes` and emits a `pairing_granted` event.
2. `hermes.connect(token, hermes_id)` raises `ValueError` when the token is empty, `ValueError` when `hermes_id` is not paired, `PermissionError` when the token is expired, and returns a `HermesConnection` on success.
3. `hermes.read_status(conn)` raises `PermissionError` if `observe` is absent; otherwise returns the miner snapshot dict.
4. `hermes.append_summary(conn, text, scope)` raises `PermissionError` if `summarize` is absent, `ValueError` if `text` is empty/whitespace, and returns a `SpineEvent` on success.
5. `hermes.get_filtered_events(conn, limit=20)` never returns an event with `kind == EventKind.USER_MESSAGE.value`.
6. All daemon `/hermes/*` HTTP endpoints return appropriate JSON with correct HTTP status codes (200, 400, 401, 403, 404).

---

## Failure Handling

| Failure | Error Code | HTTP Status |
|---|---|---|
| Missing or malformed authority token | `HERMES_INVALID_TOKEN` | 400 |
| Hermes not paired | `HERMES_NOT_PAIRED` | 400 |
| Token expired | `HERMES_TOKEN_EXPIRED` | 403 |
| Capability absent | `HERMES_UNAUTHORIZED` | 403 |
| Empty summary text | `HERMES_INVALID_SUMMARY` | 400 |
| Malformed JSON body | — | 400 |

---

## Non-Goals

- Hermes does not issue miner control commands in Milestone 1.
- The adapter does not encrypt or sign event payloads.
- There is no revocation mechanism for an already-paired Hermes token (future: `capability_revoked` event + store update).
- The daemon does not persist Hermes connections across restarts; connections are in-memory only.
