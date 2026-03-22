# Hermes Adapter Implementation — Specification

**Status:** Review (pre-implementation)
**Generated:** 2026-03-22
**Lane:** hermes-adapter-implementation

## Overview

This specification captures the contract for the Hermes adapter module: a
capability boundary between an external AI agent (Hermes) and the Zend gateway.
The adapter enforces that Hermes can observe miner status and append summaries
to the event spine, but cannot issue control commands or read user messages.

## Scope

The adapter is a Python module (`services/home-miner-daemon/hermes.py`) that
runs in-process with the daemon. It is not a separate service. It enforces
scope by filtering requests before they reach the gateway contract.

### In Scope (Milestone 1)

- Hermes pairing: register a Hermes agent with observe+summarize capabilities
- Authority token validation: verify hermes_id, expiration, capabilities
- readStatus: delegate to daemon's miner snapshot (requires observe capability)
- appendSummary: append hermes_summary to event spine (requires summarize capability)
- Event filtering: return only hermes_summary, miner_alert, control_receipt events
- Block user_message events from Hermes reads
- HTTP endpoints: /hermes/pair, /hermes/connect, /hermes/status, /hermes/summary, /hermes/events
- Reject Hermes attempts to call /miner/start, /miner/stop, /miner/set_mode (403)

### Out of Scope

- Control capability for Hermes
- Payout-target mutation
- Inbox message composition
- Contact policy model
- Encrypted payloads (deferred to transport layer)

## Data Model

### HermesConnection

    @dataclass
    class HermesConnection:
        hermes_id: str
        principal_id: str
        capabilities: list[str]  # ['observe', 'summarize']
        connected_at: str

### Capability Domain

Hermes capabilities are distinct from gateway capabilities:
- Gateway: `observe`, `control`
- Hermes: `observe`, `summarize`

These must not be conflated. A Hermes pairing record must be distinguishable
from a gateway pairing record in storage.

### Readable Events

    HERMES_READABLE_EVENTS = [
        EventKind.HERMES_SUMMARY,
        EventKind.MINER_ALERT,
        EventKind.CONTROL_RECEIPT,
    ]

Events of kind `user_message`, `pairing_requested`, `pairing_granted`, and
`capability_revoked` are filtered out before returning to Hermes.

## API Endpoints

| Endpoint | Method | Auth | Description |
|----------|--------|------|-------------|
| `/hermes/pair` | POST | None (LAN-only) | Register Hermes agent |
| `/hermes/connect` | POST | Hermes token | Validate token, return connection state |
| `/hermes/status` | GET | Hermes token | Read miner snapshot |
| `/hermes/summary` | POST | Hermes token | Append summary to spine |
| `/hermes/events` | GET | Hermes token | Read filtered events |

Auth header scheme: `Authorization: Hermes <hermes_id>`

## Dependencies

### Required (not yet implemented)

- Token auth infrastructure (plan 006): token issuance with expiration
- `store.is_token_expired()`: does not exist in store.py
- Auth middleware in daemon.py: no HTTP-level auth exists today

### Available

- `spine.append_hermes_summary()`: exists, accepts (summary_text, authority_scope: list, principal_id)
- `spine.get_events()`: exists, returns SpineEvent dataclass instances
- `spine.EventKind.HERMES_SUMMARY`: exists
- `store.pair_client()`: exists but raises on duplicate device_name (not idempotent)
- `store.get_pairing_by_device()`: exists, no expiration check
- `store.has_capability()`: exists

## Acceptance Criteria

1. Hermes can pair with observe+summarize capabilities
2. Hermes can read miner status via adapter
3. Hermes can append summaries to event spine via adapter
4. Hermes CANNOT call /miner/start, /miner/stop, /miner/set_mode (403)
5. Hermes CANNOT read user_message events (filtered)
6. Re-pairing with same hermes_id is idempotent
7. Expired tokens are rejected
8. All 8 planned tests pass

## Source Files

| File | Status | Role |
|------|--------|------|
| `services/home-miner-daemon/hermes.py` | Does not exist | Adapter module |
| `services/home-miner-daemon/daemon.py` | Exists, needs Hermes endpoints | HTTP server |
| `services/home-miner-daemon/store.py` | Exists, needs Hermes pairing support | Storage |
| `services/home-miner-daemon/spine.py` | Exists, has append_hermes_summary | Event journal |
| `services/home-miner-daemon/tests/test_hermes.py` | Does not exist | Tests |
| `scripts/hermes_summary_smoke.sh` | Exists, bypasses adapter | Smoke test |
