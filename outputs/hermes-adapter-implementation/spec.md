# Hermes Adapter Implementation — Specification

**Status:** Implemented
**Date:** 2026-03-22
**Supervisory lane:** `hermes-adapter-implementation`
**Files produced:** `services/home-miner-daemon/hermes.py`, `services/home-miner-daemon/daemon.py`, `services/home-miner-daemon/cli.py`

## Purpose

Give a remote Hermes AI agent scoped, read-only access to the Zend home-miner daemon: it may observe miner status and append summaries to the event spine, but cannot issue control commands or read private user messages.

After this slice lands, an operator can pair a Hermes agent with the daemon, and that agent can read operational state through a capability-gated adapter without any path to miner control.

## Architecture

```
Hermes Gateway → Zend Hermes Adapter → Zend Gateway (daemon) → Event Spine
                 ^^^^^^^^^^^^^^^^^^^^
                 this module
```

The adapter lives in `services/home-miner-daemon/hermes.py`. It is imported and called by the daemon (`daemon.py`) and the CLI (`cli.py`). It has no network surface of its own.

## Implemented Components

### Hermes Adapter Module — `services/home-miner-daemon/hermes.py`

#### Constants

| Name | Value | Purpose |
|------|-------|---------|
| `HERMES_CAPABILITIES` | `['observe', 'summarize']` | Full scope granted to Hermes agents |
| `HERMES_READABLE_EVENTS` | `[HERMES_SUMMARY, MINER_ALERT, CONTROL_RECEIPT]` | Whitelist of event kinds Hermes may read |
| `HERMES_BLOCKED_EVENTS` | `[USER_MESSAGE]` | Hard block — Hermes never receives these |

#### Dataclasses

**`HermesConnection`** — an active, validated session. Fields: `hermes_id`, `principal_id`, `capabilities`, `connected_at`. Method `has_capability(cap)` checks membership in the capabilities list.

**`HermesPairing`** — a persistent pairing record. Fields: `hermes_id`, `principal_id`, `device_name`, `capabilities`, `paired_at`, `token`, `token_expires_at`.

#### Exceptions

- **`HermesCapabilityError`** — raised when an action requires a capability the connection does not hold.
- **`HermesTokenError`** — raised when the authority token is missing, malformed, unknown, or mismatched.

#### Functions

| Function | Capability required | Purpose |
|----------|---------------------|---------|
| `pair_hermes(hermes_id, device_name)` | None | Create or return existing pairing record; grants `observe + summarize` |
| `connect(authority_token)` | None | Validate token, return `HermesConnection` |
| `read_status(connection, miner)` | `observe` | Return `miner.get_snapshot()` |
| `append_summary(connection, summary_text, authority_scope)` | `summarize` | Append `hermes_summary` event to spine |
| `get_filtered_events(connection, limit)` | None (read-only) | Return events filtered to readable kinds; `user_message` excluded |
| `verify_control_denied(connection)` | None | Return `True` — convenience for tests |
| `parse_hermes_auth_header(auth_header)` | None | Extract `hermes_id` from `Authorization: Hermes <id>` header |

### Daemon Endpoints — `services/home-miner-daemon/daemon.py`

The daemon's `GatewayHandler` adds five Hermes routes alongside the existing miner control routes:

| Route | Method | Auth | Behavior |
|-------|--------|------|----------|
| `/hermes/pair` | POST | None | Call `pair_hermes()`; return pairing metadata + token |
| `/hermes/connect` | POST | None | Call `connect()` with `authority_token`; store connection in `_hermes_connections` dict |
| `/hermes/status` | GET | Hermes `observe` | Call `read_status()`; return miner snapshot |
| `/hermes/summary` | POST | Hermes `summarize` | Call `append_summary()`; return event metadata |
| `/hermes/events` | GET | Hermes | Call `get_filtered_events()`; return filtered event list |

Control endpoints (`/miner/start`, `/miner/stop`, `/miner/set_mode`) return `403` with `"hermes_unauthorized"` when the `Authorization` header begins with `Hermes `. This is a second-layer defense independent of the adapter's capability checks.

### CLI Commands — `services/home-miner-daemon/cli.py`

```
zend hermes pair     --hermes-id <id> [--device-name <name>]
zend hermes connect  --hermes-id <id> [--token <token>]
zend hermes status   --hermes-id <id>
zend hermes summary  --hermes-id <id> --text <text> [--scope <scope>]
zend hermes events   --hermes-id <id>
```

CLI state is persisted to `state/hermes-cli-state.json` after pairing and connect.

## Capability Boundary

### Hermes CAN
- ✅ Read miner status via `/hermes/status` (requires `observe`)
- ✅ Append `hermes_summary` events via `/hermes/summary` (requires `summarize`)
- ✅ Read filtered events via `/hermes/events` (only `hermes_summary`, `miner_alert`, `control_receipt`)
- ✅ Pair with daemon via `/hermes/pair`

### Hermes CANNOT
- ❌ Issue control commands — `/miner/start`, `/miner/stop`, `/miner/set_mode` all return `403`
- ❌ Read `user_message` events — `get_filtered_events()` excludes them by kind whitelist
- ❌ Access any other daemon endpoint not listed above

## Event Filtering

`get_filtered_events()` fetches `limit * 2` events from the spine and returns only those whose `kind` is in `HERMES_READABLE_EVENTS`. The 2× multiplier compensates for the expectation that most events in the spine are `user_message`. If the spine is dominated by non-readable events, fewer than `limit` results are returned.

Readable kinds: `hermes_summary`, `miner_alert`, `control_receipt`.

Blocked kinds: `user_message` (the adapter explicitly holds this constant and filters it).

## Acceptance Criteria

- [x] `hermes.py` adapter module created
- [x] `HermesConnection` with authority token validation (`connect()`)
- [x] `read_status()` through adapter
- [x] `append_summary()` through adapter
- [x] Event filtering (`user_message` blocked)
- [x] Hermes pairing endpoint (`/hermes/pair`)
- [x] Hermes connect endpoint (`/hermes/connect`)
- [x] CLI with five Hermes subcommands
- [x] Control endpoints return `403` for Hermes auth

## Files

| File | Action |
|------|--------|
| `services/home-miner-daemon/hermes.py` | Created |
| `services/home-miner-daemon/daemon.py` | Modified — added Hermes routes |
| `services/home-miner-daemon/cli.py` | Modified — added Hermes subcommands |
| `services/home-miner-daemon/store.py` | Read — `load_or_create_principal`, `load_pairings`, `save_pairings`, `Principal` |
| `services/home-miner-daemon/spine.py` | Read — `EventKind`, `spine_get_events`, `append_event`, `append_hermes_summary` |
| `state/hermes-pairings.json` | Created at runtime by adapter |
| `state/hermes-cli-state.json` | Created at runtime by CLI |

## Verified Behavior

### Module self-test

```
$ python3 services/home-miner-daemon/hermes.py
Hermes Adapter Module
========================================
Capabilities: ['observe', 'summarize']
Readable events: ['hermes_summary', 'miner_alert', 'control_receipt']
Blocked events: ['user_message']

Module loaded successfully.
```

### API smoke sequence

```bash
# 1. Pair
curl -s -X POST http://127.0.0.1:8080/hermes/pair \
  -H "Content-Type: application/json" \
  -d '{"hermes_id": "hermes-001", "device_name": "hermes-agent"}'
# → {"success": true, "hermes_id": "hermes-001", "capabilities": ["observe", "summarize"], "token": "..."}

# 2. Connect
curl -s -X POST http://127.0.0.1:8080/hermes/connect \
  -H "Content-Type: application/json" \
  -d '{"authority_token": "Hermes hermes-001:<token>"}'
# → {"hermes_id": "hermes-001", "connected": true, "capabilities": ["observe", "summarize"]}

# 3. Read status
curl -s http://127.0.0.1:8080/hermes/status \
  -H "Authorization: Hermes hermes-001"
# → {"status": "stopped", "mode": "paused", ...}

# 4. Append summary
curl -s -X POST http://127.0.0.1:8080/hermes/summary \
  -H "Authorization: Hermes hermes-001" \
  -H "Content-Type: application/json" \
  -d '{"summary_text": "Miner running normally", "authority_scope": "observe"}'
# → {"appended": true, "event_id": "...", "kind": "hermes_summary"}

# 5. Control blocked
curl -s -X POST http://127.0.0.1:8080/miner/start \
  -H "Authorization: Hermes hermes-001"
# → 403 {"error": "hermes_unauthorized", "message": "HERMES_UNAUTHORIZED: control commands not permitted"}
```

## Open Items

- [ ] `tests/test_hermes.py` — boundary enforcement tests for capability scoping
- [ ] Gateway client Agent tab update for real Hermes connection state
- [ ] Smoke test script update with Hermes sequences

## Design Decisions

1. **Lookup-based token vs encoded token.** The reference contract (`references/hermes-adapter.md`) specifies an authority token that encodes principal ID, capabilities, and expiration. The implementation uses a UUID-stored token with server-side capability lookup. This is a deliberate MVP simplification. The token format is still `"Hermes <hermes_id>:<token>"` — the same surface — but the daemon validates by lookup rather than JWT decode. This must be revisited before multi-user or cross-device Hermes deployments.

2. **`user_message` blocked entirely vs read-only.** The reference contract says "read-only access to user messages." The implementation blocks `USER_MESSAGE` events entirely from Hermes. This is a deliberate privacy-first tightening. The `HERMES_BLOCKED_EVENTS` constant makes it explicit and adjustable.

3. **`import os` placement.** The `import os` statement in `hermes.py` appears after functions that reference `os.environ`. Python resolves imports at module-load time, before any function body executes, so this works — but it is fragile and will break if the functions are ever moved or if an early import fails. See review finding **H3**.
