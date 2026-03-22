# Hermes Adapter — Capability Spec

**Status:** Implemented — slice 1 of N
**Date:** 2026-03-22
**Plan:** `genesis/plans/009-hermes-adapter-implementation.md`
**Supersedes:** Nothing prior; this is a greenfield capability.

---

## Purpose / User-Visible Outcome

A Hermes AI agent can connect to the Zend home-miner daemon with an authority token and perform two actions: read the current miner status and append a text summary to the event spine. The agent cannot issue control commands (start/stop/set_mode) and cannot read user messages stored in the event spine.

Operators can observe Hermes activity through the gateway Agent tab, which shows connection state, granted capabilities, and recent summaries.

---

## Whole-System Goal

Extend the Zend daemon with a scoped adapter lane for Hermes agents. The adapter is an in-process Python module (`services/home-miner-daemon/hermes.py`) that enforces a hard trust boundary: Hermes operates within a two-capability window (`observe`, `summarize`) and is denied every other operation at the earliest possible gate in the request lifecycle.

---

## Scope

### In scope

- `HermesConnection` dataclass and session model
- `connect()` with authority-token validation and rolling TTL refresh
- `read_status()` through adapter (requires `observe`)
- `append_summary()` through adapter (requires `summarize`)
- `get_filtered_events()` that returns only `hermes_summary`, `miner_alert`, `control_receipt` — explicitly excluding `user_message`
- `pair_hermes()` / `get_hermes_pairing()` pairing management
- Daemon HTTP endpoints: `POST /hermes/pair`, `POST /hermes/connect`, `GET /hermes/status`, `POST /hermes/summary`, `GET /hermes/events`, `GET /hermes/connection`
- Control-command rejection: any `/miner/*` request carrying `Authorization: Hermes <id>` returns `403 HERMES_UNAUTHORIZED`
- CLI subcommands: `hermes-pair`, `hermes-connect`, `hermes-status`, `hermes-summary`, `hermes-events`
- Gateway Agent tab: real connection state, capability pills, connection metadata, recent summaries

### Out of scope

- Formal unit tests (deferred to plan 010)
- TTL-based session store (in-memory dict used for milestone 1)
- Hermes spline interpolation in miner simulator
- Updates to `references/hermes-adapter.md`

---

## Current State

Hermes adapter is implemented and functional. All six frontier tasks are complete. The daemon serves Hermes endpoints on the same port (8080) as the existing gateway, differentiated by path prefix. The adapter runs in-process with the daemon, not as a separate service.

---

## Architecture / Runtime Contract

```
Hermes Gateway
      |
      v
Zend Hermes Adapter  ← hermes.py (this module)
      |
      v
Zend Gateway Contract / Daemon  ← daemon.py
      |
      v
Event Spine  ← spine.py
```

**Token model:** Authority token IS the `hermes_id`. Pairing creates a record keyed by `hermes_id`; `connect()` looks it up by that key. Tokens are reusable within a 24-hour TTL window. Each `connect()` call refreshes the expiration, creating a rolling session.

**Capability model:** Hermes uses `observe` and `summarize` — distinct from the gateway's `observe` and `control`. This makes the trust model explicit and prevents accidental capability inheritance.

**Event filtering:** `HERMES_READABLE_EVENTS = [hermes_summary, miner_alert, control_receipt]`. `user_message` is explicitly excluded at the adapter layer before any event data reaches Hermes.

**Session store:** In-memory `Dict[str, HermesConnection]` on `GatewayHandler`. Production should use a TTL-based store.

---

## Adoption Path

1. Start the daemon: `python3 services/home-miner-daemon/daemon.py`
2. Pair a Hermes agent: `python3 cli.py hermes-pair --hermes-id <id> --device-name <name>`
3. Note the `authority_token` in the response (equals `hermes_id`)
4. Agent uses `hermes-status`, `hermes-summary`, `hermes-events` CLI commands or HTTP endpoints
5. Gateway Agent tab at `http://127.0.0.1:8080/` shows live connection state

---

## Acceptance Criteria

| Criterion | How to verify |
|-----------|---------------|
| Hermes can pair and receive an authority token | `hermes-pair` returns token |
| Hermes can connect and receive a session | `hermes-connect` returns session dict |
| `hermes-status` reads miner snapshot | Output includes `status`, `mode`, `hashrate_hs` |
| `hermes-summary` appends to spine | `hermes-events` shows new `hermes_summary` event |
| `hermes-events` excludes `user_message` | `user_message` events never appear |
| Control commands rejected for Hermes | `curl /miner/start` with Hermes auth → 403 |
| CLI commands return correct exit codes | 0 on success, 1 on error |
| Gateway Agent tab reflects real state | Page shows live connection metadata |

---

## Failure Handling

| Failure | Response |
|---------|----------|
| Invalid/expired token | `401 hermes_invalid_token` with message |
| Missing capability | `403 hermes_unauthorized` with required cap name |
| Empty summary text | `400 hermes_invalid_summary` |
| Daemon unreachable | CLI returns exit code 1, `daemon_unavailable` in body |
| Missing Authorization header | `403 hermes_unauthorized` |
| Not yet paired | `401` from `connect()` via `_decode_authority_token` |
