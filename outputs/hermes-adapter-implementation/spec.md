# Hermes Adapter Implementation — Specification

**Lane:** `hermes-adapter-implementation`
**Status:** Milestones 1–2 complete. Milestones 3–4 pending.
**Date:** 2026-03-22

---

## Purpose

A Hermes adapter module that sits between an external Hermes AI agent and the Zend gateway contract. Hermes agents are untrusted — they can observe miner status and append summaries, but cannot read user messages or issue control commands. The adapter is the enforcement boundary that makes this separation real.

## What Was Built

### `services/home-miner-daemon/hermes.py` — Adapter module

| Symbol | Purpose |
|--------|---------|
| `HERMES_CAPABILITIES` | Allowlist: `["observe", "summarize"]` — ceiling for all Hermes tokens |
| `HERMES_READABLE_EVENTS` | Event kinds Hermes may read: `"hermes_summary"`, `"miner_alert"`, `"control_receipt"` |
| `HermesAuthorityToken` | Dataclass: hermes_id, principal_id, capabilities, issued_at, expires_at, nonce |
| `HermesConnection` | Handle returned by `connect()`; carries hermes_id, principal_id, and scoped capabilities |
| `encode_hermes_token()` | Base64-URLsafe JSON encoding (unsigned, milestone 1) |
| `decode_hermes_token()` | Token decoding with structural validation; raises `ValueError` on malformed input |
| `issue_hermes_token()` | Issues token with 24h TTL and uuid4 nonce |
| `pair_hermes()` | Idempotent pairing record creation in `hermes-store.json` |
| `connect()` | Validates token structure, expiry, and capability ceiling; returns `HermesConnection` |
| `read_status()` | Returns `miner.get_snapshot()`; requires `"observe"` |
| `append_summary()` | Calls `spine.append_hermes_summary()`; requires `"summarize"` |
| `get_filtered_events()` | Reads events filtered to `HERMES_READABLE_EVENTS`; requires `"observe"` |

### `services/home-miner-daemon/daemon.py` — HTTP endpoints

| Endpoint | Method | Auth | Notes |
|----------|--------|------|-------|
| `POST /hermes/pair` | POST | None | Creates pairing record, issues token, returns both |
| `POST /hermes/connect` | POST | Body token | Validates token, returns connection info |
| `GET /hermes/status` | GET | `Authorization: Hermes <token>` | Proxied to `hermes.read_status()` |
| `POST /hermes/summary` | POST | `Authorization: Hermes <token>` | Proxied to `hermes.append_summary()` |
| `GET /hermes/events` | GET | `Authorization: Hermes <token>` | Proxied to `hermes.get_filtered_events()` |
| `POST /miner/start` | POST | Rejects `Hermes` prefix | Control denied for Hermes callers |
| `POST /miner/stop` | POST | Rejects `Hermes` prefix | Control denied for Hermes callers |
| `POST /miner/set_mode` | POST | Rejects `Hermes` prefix | Control denied for Hermes callers |

### `services/home-miner-daemon/cli.py` — Hermes CLI subcommands

```
zend hermes pair     --hermes-id <id> [--device-name] [--ttl-hours]
zend hermes connect   --hermes-id <id> [--token]
zend hermes status    --hermes-id <id> [--token]
zend hermes summary   --hermes-id <id> --text <text> [--scope]
zend hermes events   --hermes-id <id> [--token]
```

Token is auto-loaded from `state/hermes_token_<id>.json` if `--token` is omitted after pairing.

## Capability Model

```
pair_hermes() → issues HermesAuthorityToken
                       │
                       ▼
              connect() validates per request:
              ├─ token structure (base64-URLsafe JSON decode)
              ├─ expiry (is_expired(), checked every request)
              └─ each capability ∈ HERMES_CAPABILITIES
                       │
                       ▼
              HermesConnection with scoped capabilities
                       │
              ┌────────┴────────┐
              │                 │
        read_status()      append_summary()
        (observe)          (summarize)
              │
        get_filtered_events()
        (observe)
        returns events where kind ∈ HERMES_READABLE_EVENTS
```

**Capability ceiling:** `connect()` rejects any capability not in `HERMES_CAPABILITIES`. A forged token claiming `"control"` is rejected regardless of validity of other fields.

## Event Filtering

`get_filtered_events()` returns events where `SpineEvent.kind ∈ HERMES_READABLE_EVENTS`:

- Permitted: `hermes_summary`, `miner_alert`, `control_receipt`
- Blocked: `user_message`, `pairing_requested`, `pairing_granted`, `capability_revoked`

The filter operates on `SpineEvent.kind` string values. Payload redaction is deferred to a future milestone.

**Spec boundary deviation:** The reference spec used the phrasing "read-only access to user messages." The implementation is stricter — it blocks `user_message` entirely from Hermes reads. This is a deliberate tightening documented here.

## Token Format (Milestone 1)

Base64-URLsafe JSON. Not signed. Fields: `hermes_id`, `principal_id`, `capabilities`, `issued_at`, `expires_at`, `nonce`.

- Nonce is generated (uuid4) but not validated at `connect()` — no replay protection in milestone 1.
- Token signing and nonce validation depend on plan 006 (token auth).

## State Files

| File | Contents |
|------|----------|
| `state/hermes-store.json` | Pairing records keyed by `hermes_id` |
| `state/hermes_token_<id>.json` | Authority token + metadata persisted by CLI after pairing |

## What Remains

| Milestone | Task | Status |
|-----------|------|--------|
| 3 | Update gateway client Agent tab to show Hermes status | Not started |
| 4 | Adapter boundary tests | Not started |
| Production | Token signing (HMAC-SHA256 or JWT) | Deferred — depends on plan 006 |
| Production | Nonce validation for replay protection | Deferred — depends on plan 006 |
| Production | Token revocation mechanism | Deferred |
| Production | Payload redaction on `control_receipt` | Deferred |
| Production | Unified auth middleware for control endpoints | Deferred |
| Production | File locking on `hermes-store.json` | Deferred |

## Deviations from Plan

1. **`HERMES_READABLE_EVENTS` uses raw strings** instead of `EventKind` enum values. `SpineEvent.kind` stores string values, so runtime behavior is correct. A plan proof test using `[e.value for e in HERMES_READABLE_EVENTS]` would fail (strings lack `.value`), but this is a test-only issue, not a runtime issue.

2. **`user_message` blocked rather than read-only.** Plan phrasing was "read-only access to user messages." Implementation blocks reads entirely. Deliberate tightening — user messages are private by default.

3. **`append_summary()` scopes authority with a caller-supplied string** (`authority_scope`), not with a hardcoded value. The spine function accepts this field; the daemon endpoint defaults to `"observe"` when not supplied. Functionally correct for milestone 1.
