# Hermes Adapter — Capability Spec

**Status:** Accepted
**Frontier:** `hermes-adapter`
**Generated:** 2026-03-23

## Purpose / User-Visible Outcome

After this work, Hermes Gateway can connect to the Zend home-miner daemon through a
Zend-native adapter layer. Hermes receives only the capabilities Zend explicitly
grants, and every Hermes action is audited in the same encrypted event spine that
already backs the operations inbox. Hermes cannot observe user messages, cannot
mutate miner payout targets, and cannot issue direct control commands in
milestone 1.

## Whole-System Goal

Hermes is an agent that runs alongside the Zend home-miner daemon. Zend owns the
canonical gateway contract so Hermes never becomes the internal skeleton of the
product. The adapter enforces all capability boundaries before forwarding any
Hermes request to the daemon or the event spine.

## Scope

This spec covers the first honest slice of the Hermes adapter frontier:

- `hermes.py` adapter module inside `services/home-miner-daemon/`
- `HermesConnection` class with authority token validation
- `readStatus` routed through the adapter to the daemon
- `appendSummary` routed through the adapter to the event spine
- Event filtering: Hermes may not read `user_message` events from the spine
- Hermes pairing endpoint added to the daemon HTTP surface
- Smoke test script exercising the full adapter flow

## Current State

Today `scripts/hermes_summary_smoke.sh` appends a Hermes summary directly to the
event spine by importing from `store` and `spine`. It bypasses any adapter layer
and has no authority token validation. The daemon HTTP surface has no Hermes
pairing endpoint and no adapter-aware routes.

## Architecture / Runtime Contract

### Adapter Module

```
services/home-miner-daemon/hermes.py
```

The adapter exposes a single `HermesConnection` class that wraps an HTTP session
to the daemon and enforces capability boundaries locally before making daemon
calls.

```python
class HermesConnection:
    def __init__(self, authority_token: str, daemon_url: str)
    def readStatus(self) -> MinerSnapshot
    def appendSummary(self, summary_text: str) -> SpineEvent
    def getScope(self) -> list[HermesCapability]
    def close(self)
```

### Authority Token

The authority token is a JWT-like opaque string issued by the daemon during the
Hermes pairing handshake. It encodes:

- `principal_id`: the Zend `PrincipalId` this Hermes instance operates under
- `capabilities`: the granted `HermesCapability` set (`observe`, `summarize`)
- `expires_at`: ISO 8601 UTC timestamp

The token is validated on every `HermesConnection` operation. Expired or missing
tokens raise `HermesUnauthorized`.

### HermesCapabilities

```python
HermesCapability = Literal["observe", "summarize"]
```

**Milestone 1:**
- `observe` — Hermes may call `readStatus` to get a `MinerSnapshot`
- `summarize` — Hermes may call `appendSummary` to write a `hermes_summary` event

Direct miner `control` is explicitly out of scope for milestone 1.

### MinerSnapshot

The `MinerSnapshot` returned by `readStatus` has this shape:

```python
@dataclass
class MinerSnapshot:
    status: MinerStatus        # running | stopped | offline | error
    mode: MinerMode            # paused | balanced | performance
    hashrate_hs: int
    temperature: float
    uptime_seconds: int
    freshness: str             # ISO 8601 UTC
```

This is identical to the snapshot the daemon already returns to paired gateway
clients.

### Event Spine Access

Hermes may read from the spine:
- `hermes_summary` — its own summaries
- `miner_alert` — alerts it may have generated
- `control_receipt` — to understand recent actions

Hermes may write to the spine:
- `hermes_summary` — only via `appendSummary`, which the adapter enforces

Hermes may **never** read:
- `user_message` — blocked by the adapter before the daemon call

### Pairing Endpoint

The daemon adds one new HTTP route:

```
POST /hermes/pair
Body: { "device_name": string, "requested_capabilities": HermesCapability[] }
200: { "authority_token": string, "granted_capabilities": HermesCapability[] }
400: { "error": "invalid_capability" }
401: { "error": "unauthorized" }
```

This is the only entry point for Hermes to receive an authority token. The
daemon records the Hermes pairing in the event spine as a `pairing_requested` /
`pairing_granted` pair just as it does for gateway clients.

### Error Classes

| Class | When Raised |
|---|---|
| `HermesUnauthorized` | token missing, expired, or replayed |
| `HermesCapabilityDenied` | requested capability not in granted set |
| `HermesEventBlocked` | Hermes attempted to read `user_message` events |
| `HermesDaemonUnavailable` | daemon HTTP endpoint unreachable |

## Adapter Method Contracts

### `__init__(authority_token: str, daemon_url: str)`

Decodes and validates the authority token. Raises `HermesUnauthorized` if the
token is malformed, expired, or has already been used (replay detection via a
nonce in the token payload). Stores validated claims for use in subsequent calls.

### `readStatus() -> MinerSnapshot`

Requires `observe` in the token's capability set. Raises
`HermesCapabilityDenied` otherwise. Calls `GET /status` on the daemon and returns
the snapshot. Does not route through the event spine — the daemon returns the
snapshot directly.

### `appendSummary(summary_text: str) -> SpineEvent`

Requires `summarize` in the token's capability set. Raises
`HermesCapabilityDenied` otherwise. Calls `append_hermes_summary` in `spine.py`
with `principal_id` from the token and returns the resulting `SpineEvent`.

The adapter does **not** pass `user_message` events to Hermes under any
circumstance. Any spine read path that would expose `user_message` events must
be gated in the daemon before returning results to the adapter.

### `getScope() -> list[HermesCapability]`

Returns the validated capability list from the token. No side effects.

### `close()`

Closes the HTTP session. Idempotent.

## Adoption Path

The adapter is adopted by the daemon first. The daemon gains a `/hermes/pair`
endpoint and adapter-aware routes. The `hermes_summary_smoke.sh` script is
replaced with a Python smoke test that uses `HermesConnection` directly, proving
the authority token flow and event filtering end-to-end.

The thin gateway client in `apps/zend-home-gateway/` gains an **Agent** tab that
shows Hermes connection state, granted scope, and recent Hermes summaries pulled
from the event spine.

## Acceptance Criteria

1. `HermesConnection(authority_token, daemon_url)` raises `HermesUnauthorized`
   when given a missing, malformed, expired, or replayed token.
2. `connection.readStatus()` raises `HermesCapabilityDenied` when the token
   lacks `observe`.
3. `connection.appendSummary("...")` raises `HermesCapabilityDenied` when the
   token lacks `summarize`.
4. `connection.appendSummary("...")` succeeds and returns a `SpineEvent` when
   the token has `summarize`; the event is visible in `spine.get_events(kind=
   EventKind.HERMES_SUMMARY)`.
5. `POST /hermes/pair` with valid body returns a JWT-like authority token
   containing `principal_id`, `capabilities`, and `expires_at`.
6. The adapter blocks all `user_message` event access — the daemon never returns
   them to Hermes.
7. The daemon records a `pairing_granted` event in the spine when Hermes pairs.
8. The Python smoke test (`scripts/hermes_adapter_smoke.py`) passes with a valid
   token and fails with a missing or expired token.

## Failure Handling

If the daemon is offline when Hermes calls `readStatus`, the adapter raises
`HermesDaemonUnavailable` with a message that names the daemon URL. The Hermes
side retries with backoff.

If the authority token expires mid-session, the next adapter call raises
`HermesUnauthorized`. Hermes must re-pair via `/hermes/pair` to receive a new
token.

If Hermes attempts to read `user_message` events, the adapter raises
`HermesEventBlocked` before the daemon is called. This is enforced at the adapter
boundary, not inside the daemon, so the violation is visible and auditable even
if the daemon has a bug.

## Non-Goals

- Hermes control capability (deferred to post-milestone-1 capability model)
- Hermes direct miner command injection (requires stronger audit trail)
- Hermes inbox message composition or reading (requires contact policy model)
- Real Hermes Gateway live integration (simulated by the adapter in milestone 1)
