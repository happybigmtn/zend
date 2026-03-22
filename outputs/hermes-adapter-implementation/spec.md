# Hermes Adapter Implementation — Specification

**Status:** Not Implemented (specify stage produced no artifacts)
**Lane:** `hermes-adapter-implementation`
**Generated:** 2026-03-22

## Overview

This spec documents the frontier tasks for the Hermes adapter implementation
lane and the gap between what the lane contract requires and what currently
exists in the codebase.

## Frontier Tasks (from lane contract)

1. Create `hermes.py` adapter module
2. Implement `HermesConnection` with authority token validation
3. Implement `readStatus` through adapter
4. Implement `appendSummary` through adapter
5. Implement event filtering (block `user_message` events for Hermes)
6. Add Hermes pairing endpoint to daemon

## What Exists Today

### Contract Documents

- `references/hermes-adapter.md` — Defines the adapter interface, capability
  scope (`observe` | `summarize`), authority token structure, event spine access
  rules, and milestone 1 boundaries.
- `references/event-spine.md` — Defines `EventKind` enum including
  `hermes_summary`, payload schemas, and routing rules.
- `references/inbox-contract.md` — Defines `PrincipalId` shared across gateway
  and inbox.

### Implementation Code

- `services/home-miner-daemon/spine.py` — Has `append_hermes_summary()` and
  `get_events()` functions that the adapter would wrap.
- `services/home-miner-daemon/store.py` — Has `pair_client()`,
  `has_capability()`, and principal management that the adapter would use for
  authority checks.
- `services/home-miner-daemon/daemon.py` — HTTP server with `/status`,
  `/health`, and `/miner/*` endpoints. No Hermes-specific endpoints exist.
- `scripts/hermes_summary_smoke.sh` — Exists but bypasses any adapter boundary.
  Calls `spine.append_hermes_summary()` directly with no capability check.

### What Does NOT Exist

- No `hermes.py` module anywhere in the codebase.
- No `HermesConnection` class or authority token validation.
- No adapter-mediated `readStatus` or `appendSummary`.
- No event filtering that blocks `user_message` events from Hermes.
- No `/hermes/pair` or `/hermes/*` endpoints in `daemon.py`.
- No `outputs/hermes-adapter-implementation/` artifacts prior to this review.

## Specify Stage Result

The specify stage ran with model `MiniMax-M2.7-highspeed` and produced
**0 tokens in / 0 tokens out**. No code, no spec, no artifacts. The lane
advanced to the review stage with nothing implemented.

## Required Implementation Shape

Based on the contract in `references/hermes-adapter.md` and the existing
daemon code, the adapter implementation should:

### 1. `services/home-miner-daemon/hermes.py`

A new module containing:

- `HermesConnection` class that holds a validated authority token and the
  granted capability set (`observe`, `summarize`).
- `connect(authority_token: str) -> HermesConnection` that validates the token
  against the pairing store, checks expiration, and returns a scoped connection.
- `read_status(conn: HermesConnection) -> dict` that checks `observe` capability
  and delegates to `daemon.miner.get_snapshot()`.
- `append_summary(conn: HermesConnection, summary_text: str) -> SpineEvent` that
  checks `summarize` capability and delegates to `spine.append_hermes_summary()`.
- `get_events(conn: HermesConnection, kind: EventKind, limit: int) -> list` that
  filters out `user_message` events regardless of request.

### 2. Daemon Endpoints

New routes in `daemon.py` or a separate handler:

- `POST /hermes/pair` — Issue an authority token for a Hermes agent with
  `observe` + `summarize` capabilities only.
- `GET /hermes/status` — Read miner status through adapter (requires valid
  authority token in header).
- `POST /hermes/summary` — Append summary through adapter (requires valid
  authority token).
- `GET /hermes/events` — Read filtered events through adapter (blocks
  `user_message`).

### 3. Event Filtering

The adapter must enforce that Hermes can only read:
- `hermes_summary` (its own)
- `miner_alert`
- `control_receipt`

And must block:
- `user_message` (private user content)
- `pairing_requested` / `pairing_granted` / `capability_revoked` (trust
  ceremony internals)

### 4. Authority Token

The token must encode:
- Principal ID (the Hermes agent's identity)
- Granted capabilities (`observe`, `summarize`)
- Expiration time

Token validation must reject expired tokens and replayed tokens.

## Dependencies

This lane depends on:
- `private-control-plane@reviewed` — PrincipalId, pairing store, event spine
- `home-miner-service@reviewed` — Daemon, miner simulator, CLI

Both dependencies appear satisfied by existing code in
`services/home-miner-daemon/`.

## Acceptance Criteria

- [ ] `hermes.py` module exists with `HermesConnection` class
- [ ] Authority token validation rejects expired and replayed tokens
- [ ] `readStatus` works through adapter with `observe` capability check
- [ ] `appendSummary` works through adapter with `summarize` capability check
- [ ] Event filtering blocks `user_message` events for Hermes connections
- [ ] Daemon exposes Hermes pairing endpoint
- [ ] `hermes_summary_smoke.sh` routes through adapter instead of direct spine call
- [ ] No Hermes path can issue miner control commands
- [ ] No Hermes path can read `user_message` events
