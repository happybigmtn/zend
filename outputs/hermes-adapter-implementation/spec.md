# Hermes Adapter Implementation — Specification

**Lane:** hermes-adapter-implementation
**Date:** 2026-03-22
**Status:** Milestone 1 complete (Milestones 1-2 + CLI)

## What Was Built

A Python adapter module that mediates between external Hermes agents and the Zend gateway contract. The adapter enforces a capability ceiling: Hermes agents can only observe miner status and append summaries to the event spine. Control commands and user message events are blocked.

## Delivered Surfaces

### hermes.py — Adapter Module

| Symbol | Purpose |
|--------|---------|
| `HermesAuthorityToken` | Dataclass encoding hermes_id, principal_id, capabilities, issued_at, expires_at, nonce |
| `HermesConnection` | Handle returned by `connect()`, carries capability set |
| `HERMES_CAPABILITIES` | Allowlist: `['observe', 'summarize']` |
| `HERMES_READABLE_EVENTS` | Event kinds Hermes may read: `hermes_summary`, `miner_alert`, `control_receipt` |
| `encode_hermes_token()` | Base64-JSON token encoding (unsigned, milestone 1) |
| `decode_hermes_token()` | Token decoding with structural validation |
| `issue_hermes_token()` | Token issuance with TTL and nonce |
| `pair_hermes()` | Idempotent pairing record creation |
| `connect()` | Token validation → HermesConnection (checks expiry + capability allowlist) |
| `read_status()` | Miner snapshot via adapter (requires `observe`) |
| `append_summary()` | Event spine append (requires `summarize`) |
| `get_filtered_events()` | Event read with user_message filtering (requires `observe`) |

### daemon.py — HTTP Endpoints

| Endpoint | Method | Auth | Purpose |
|----------|--------|------|---------|
| `/hermes/pair` | POST | None | Create Hermes pairing, issue token |
| `/hermes/connect` | POST | Body token | Validate token, return connection info |
| `/hermes/status` | GET | `Authorization: Hermes <token>` | Read miner status through adapter |
| `/hermes/summary` | POST | `Authorization: Hermes <token>` | Append summary to spine |
| `/hermes/events` | GET | `Authorization: Hermes <token>` | Read filtered events |
| `/miner/start` | POST | Rejects `Hermes` prefix | Control denied for Hermes |
| `/miner/stop` | POST | Rejects `Hermes` prefix | Control denied for Hermes |
| `/miner/set_mode` | POST | Rejects `Hermes` prefix | Control denied for Hermes |

### cli.py — Hermes Subcommands

| Command | Purpose |
|---------|---------|
| `zend hermes pair` | Pair agent, issue token, persist to state file |
| `zend hermes connect` | Validate token via daemon |
| `zend hermes status` | Read miner status through adapter |
| `zend hermes summary` | Append summary to spine |
| `zend hermes events` | Read filtered events |

## Capability Model

```
Token issued at pairing
        │
        ▼
  connect() validates:
  ├─ token structure (base64-JSON decode)
  ├─ expiration (is_expired check)
  └─ capabilities ⊆ HERMES_CAPABILITIES
        │
        ▼
  HermesConnection with scoped capabilities
        │
        ├─ read_status() → requires 'observe'
        ├─ append_summary() → requires 'summarize'
        └─ get_filtered_events() → requires 'observe'
                                   filters to HERMES_READABLE_EVENTS
```

Capability ceiling: `connect()` rejects any capability not in `HERMES_CAPABILITIES`. Tokens cannot escalate beyond `observe` + `summarize` regardless of what they claim.

## Event Filtering

Hermes reads are filtered to: `hermes_summary`, `miner_alert`, `control_receipt`.
Blocked: `user_message`, `pairing_requested`, `pairing_granted`, `capability_revoked`.

Payloads are returned unredacted in milestone 1. Field-level redaction deferred.

## Token Format (Milestone 1)

Base64-encoded JSON. Not signed. Fields: hermes_id, principal_id, capabilities, issued_at, expires_at, nonce.

Nonce is generated but not validated for replay protection. Token signing and nonce validation are deferred to the token auth plan (plan 006).

## Deviations from Plan

1. `HERMES_READABLE_EVENTS` uses raw strings instead of `EventKind` enum values. Functionally correct (SpineEvent.kind stores string values), but loses type-level linkage.
2. Plan proof test `[e.value for e in HERMES_READABLE_EVENTS]` would fail against the implementation (strings lack `.value`). Runtime behavior is unaffected.
3. Spec boundary says "Read-only access to user messages" — implementation is stricter, blocking user_message reads entirely. This is a deliberate tightening.
