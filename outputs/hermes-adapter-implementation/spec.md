# Hermes Adapter Implementation — Spec

**Status:** Draft
**Frontier:** `hermes-adapter-implementation`
**Author:** Codex (polish lane)
**Date:** 2026-03-22

## Purpose / User-Visible Outcome

After this slice lands, Hermes Gateway can connect to the Zend home-miner daemon through a typed adapter module that enforces capability scoping at the boundary. Hermes agents and scripts can call `hermes.py readStatus` and `hermes.py appendSummary` exactly as they would against any other Hermes-compatible device, but every call passes through Zend's adapter layer which validates the authority token, filters events, and routes only to explicitly granted capabilities.

Concretely:
- `python -m services.home_miner_daemon.hermes readStatus --client hermes-gateway` prints a `MinerSnapshot` when Hermes holds `observe` and fails with a named `GatewayUnauthorized` when it does not.
- `python -m services.home_miner_daemon.hermes appendSummary --client hermes-gateway --text "..."` appends a `hermes_summary` event to the event spine when Hermes holds `summarize` and fails cleanly otherwise.
- `python -m services.home_miner_daemon.hermes events --client hermes-gateway` returns spine events filtered so that `user_message` events are never visible to Hermes in milestone 1.
- `python -m services.home_miner_daemon.hermes pair --device hermes-gateway --capabilities observe` adds a Hermes pairing record to the daemon, distinct from the existing `pair` CLI subcommand.

## Whole-System Goal

The Zend product spec defines one event spine as the source of truth and an inbox as its derived view. The Hermes adapter is the enforced boundary at which Hermes Gateway enters that system: it is the only path Hermes uses to read miner state or write summaries, and it is the only enforcement point that keeps Hermes authority inside the milestone-1 observe-only + summarize-only box.

## Scope

### In scope

- `services/home_miner_daemon/hermes.py`: new adapter module
- `HermesConnection` class with authority token validation
- `readStatus()` method: translates daemon `/status` snapshot into a Hermes-compatible dict
- `appendSummary()` method: appends a `hermes_summary` event to the spine
- Event filtering: `user_message` events are blocked for Hermes in milestone 1
- `pair` subcommand: creates a Hermes-specific pairing record with `HermesCapability` scope
- Integration into the existing `daemon.py` handler as a new route group
- Token-validation guard on every adapter method

### Out of scope

- Direct miner control through Hermes (deferred past milestone 1)
- Payout-target mutation
- Inbox message composition by Hermes
- Hermes access to `user_message` events
- Remote internet-facing Hermes connections (milestone 1 is LAN-only)

## Architecture / Runtime Contract

```
Hermes Gateway (external)
       |
       v
services/home_miner_daemon/hermes.py  ← HermesConnection, new
       |
       +-- validates authority token
       +-- checks HermesCapability scope
       +-- readStatus() → daemon /status endpoint
       +-- appendSummary() → spine.append_hermes_summary()
       +-- events() → spine.get_events() with user_message filter
       |
       v
daemon.py (existing GatewayHandler)
       |
       v
spine.py (existing append-only journal)
```

### HermesCapability enum

```python
class HermesCapability(str, Enum):
    OBSERVE = "observe"   # can call readStatus()
    SUMMARIZE = "summarize"  # can call appendSummary()
```

### HermesPairing store

Stored alongside the existing `pairing-store.json` under a separate key `hermes_pairings`. Each record:

```python
@dataclass
class HermesPairing:
    id: str
    principal_id: str
    device_name: str          # e.g. "hermes-gateway"
    capabilities: list[HermesCapability]
    paired_at: str
    token_expires_at: str
    token_used: bool = False
```

### Authority token

The daemon issues a bearer token during Hermes pairing. Every Hermes adapter method validates this token before executing. Invalid or expired tokens raise `GatewayUnauthorized`.

### Event filtering contract

`HermesConnection.events()` must filter out `user_message` events before returning them. This is the milestone-1 enforcement boundary that prevents Hermes from reading user message content.

## Decision Log

- Decision: Hermes uses a separate pairing store (`hermes_pairings` key in the same JSON file) rather than mixing Hermes and client records.
  Rationale: Hermes has its own capability vocabulary (`observe`/`summarize`) which differs from the client vocabulary (`observe`/`control`). Keeping separate stores avoids type confusion and makes the audit trail cleaner.
  Date: 2026-03-22

- Decision: Hermes adapter is a single `hermes.py` module, not a package.
  Rationale: The adapter is thin and focused. A single file with a class and CLI entry point is easier to review and test than a multi-file module at this stage.
  Date: 2026-03-22

- Decision: The `hermes pair` subcommand is separate from the existing `zend pair` subcommand.
  Rationale: The existing `pair` command uses the client capability vocabulary. A separate entry point avoids capability-type confusion and keeps the Hermes authority model explicit.
  Date: 2026-03-22

- Decision: `user_message` events are blocked at the adapter layer, not the spine layer.
  Rationale: Blocking at the spine would change the shared event-spine contract, which is used by all clients. Blocking at the adapter keeps the spine unchanged and makes the Hermes boundary explicit.
  Date: 2026-03-22

## Acceptance Criteria

1. `python -m services.home_miner_daemon.hermes pair --device hermes-gateway --capabilities observe,summarize` creates a `HermesPairing` record and prints success JSON.
2. `python -m services.home_miner_daemon.hermes readStatus --client hermes-gateway` prints a `MinerSnapshot` dict with keys `status`, `mode`, `hashrate_hs`, `temperature`, `uptime_seconds`, `freshness` when Hermes has `observe` capability.
3. `python -m services.home_miner_daemon.hermes readStatus --client hermes-gateway` exits non-zero with `GatewayUnauthorized` when Hermes lacks `observe` capability.
4. `python -m services.home_miner_daemon.hermes appendSummary --client hermes-gateway --text "test summary"` appends a `hermes_summary` event to `state/event-spine.jsonl` when Hermes has `summarize` capability.
5. `python -m services.home_miner_daemon.hermes appendSummary --client hermes-gateway --text "test"` exits non-zero with `GatewayUnauthorized` when Hermes lacks `summarize`.
6. `python -m services.home_miner_daemon.hermes events --client hermes-gateway` returns spine events but contains zero `user_message` entries.
7. The authority token is validated on every adapter method call; replayed or expired tokens raise `GatewayUnauthorized`.
8. All new methods are exercised by unit tests in `services/home_miner_daemon/test_hermes.py`.

## Failure Handling

| Codepath | Named Error | User/Agent Sees |
|---|---|---|
| Hermes calls `readStatus` without `observe` | `GatewayUnauthorized` | clean error JSON, non-zero exit |
| Hermes calls `appendSummary` without `summarize` | `GatewayUnauthorized` | clean error JSON, non-zero exit |
| Hermes calls `events` | filtered (no `user_message`) | only allowed event kinds returned |
| Invalid or expired token presented | `GatewayUnauthorized` | clean error JSON, non-zero exit |
| Hermes device not found | `HermesNotFound` | clean error JSON, non-zero exit |
| Daemon offline | `GatewayUnavailable` | clean error JSON, non-zero exit |

## What Is Superseded

Nothing. This is the first slice of the Hermes adapter boundary defined in the Zend product spec.

## Context and Orientation (for a Novice)

The repository root holds:
- `services/home_miner_daemon/daemon.py`: the LAN-only HTTP server with `/status`, `/miner/start`, `/miner/stop`, `/miner/set_mode` routes
- `services/home_miner_daemon/spine.py`: append-only event journal (`event-spine.jsonl`), exposes `append_hermes_summary()`, `get_events()`, and other helpers
- `services/home_miner_daemon/store.py`: `Principal` and `GatewayPairing` records, `pairing-store.json`
- `services/home_miner_daemon/cli.py`: the `zend` CLI with `status`, `pair`, `control`, `events` subcommands

The new file `services/home_miner_daemon/hermes.py` follows the same patterns:
- same `STATE_DIR` resolution via `Path(__file__).resolve().parents[2]`
- same JSON file layout for persistence
- same `datetime.now(timezone.utc).isoformat()` for timestamps
- same dataclass style (`@dataclass`, `asdict`)
- same error-response shape (`{"error": "NamedError", "message": "..."}`)

The `HermesPairing` record lives in the same `pairing-store.json` file but under the key `hermes_pairings` (dict keyed by pairing ID). The existing `pairing-store.json` schema is preserved for all non-Hermes records.

Key terms:
- **authority token**: bearer token issued to Hermes during pairing; validated on every adapter call
- **HermesCapability**: `observe` (read status) or `summarize` (append summary); milestone 1 has no `control`
- **event spine**: append-only journal; source of truth for all operational events
- **user_message filter**: adapter-layer enforcement that `user_message` events never reach Hermes
