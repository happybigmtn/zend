# Hermes Adapter Implementation — Specification

**Lane:** hermes-adapter-implementation
**Plan:** genesis/plans/009-hermes-adapter-implementation.md
**Date:** 2026-03-22

## Scope

The Hermes adapter is a Python module (`hermes.py`) in the home-miner daemon that enforces a capability boundary between an external AI agent (Hermes) and the Zend gateway contract. Hermes may observe miner status and append summaries, but never issue control commands or read user messages.

## Architecture

```
Hermes Gateway → Zend Hermes Adapter → Zend Gateway Contract → Event Spine
                 ^^^^^^^^^^^^^^^^^^^^
                 hermes.py + daemon.py endpoints
```

## Capability Model

| Capability | Allows | Hermes M1 |
|-----------|--------|-----------|
| observe | Read miner status, read filtered events | YES |
| summarize | Append hermes_summary events to spine | YES |
| control | Start/stop miner, set mode | NO — rejected at adapter boundary |

## Authority Token

JSON-encoded compact string with fields: `version`, `hermes_id`, `principal_id`, `capabilities`, `issued_at`, `expires_at`. Issued during pairing, validated on every connect. Version 1.

Validation chain:
1. Decode JSON structure
2. Check version == 1
3. Check expiration (UTC)
4. Validate capabilities subset of `['observe', 'summarize']`
5. Verify pairing record exists for hermes_id
6. Cross-validate principal_id against pairing record
7. Check server-side pairing expiration

## Event Filtering

Hermes reads only: `hermes_summary`, `miner_alert`, `control_receipt`.
Hermes writes only: `hermes_summary`.
`user_message` is excluded from all Hermes read paths.

## Daemon Endpoints

| Method | Path | Auth | Purpose |
|--------|------|------|---------|
| POST | /hermes/pair | None (LAN-only M1) | Create Hermes pairing record |
| POST | /hermes/connect | Body: authority_token | Validate token, establish session |
| GET | /hermes/status | Header: Hermes \<token\> | Read miner snapshot |
| POST | /hermes/summary | Header: Hermes \<token\> | Append summary to spine |
| GET | /hermes/events | Header: Hermes \<token\> | Read filtered events |

Control endpoints (`/miner/start`, `/miner/stop`, `/miner/set_mode`) reject `Authorization: Hermes` with 403.

## CLI Subcommands

`cli.py hermes pair|status|summary|events` — CLI wrappers that build tokens from stored pairing records and call daemon endpoints.

## Pairing

Idempotent. Re-pairing the same hermes_id refreshes the expiration (30 days). Pairing records stored in `hermes-pairing-store.json`, separate from gateway pairings.

## Files

| File | Role |
|------|------|
| services/home-miner-daemon/hermes.py | Adapter module: token validation, capability enforcement, event filtering |
| services/home-miner-daemon/daemon.py | HTTP endpoints for Hermes |
| services/home-miner-daemon/cli.py | CLI hermes subcommands |
| services/home-miner-daemon/spine.py | Event spine (append_hermes_summary) |
| services/home-miner-daemon/store.py | Hermes pairing persistence |
| services/home-miner-daemon/tests/test_hermes.py | 11 boundary enforcement tests |

## Test Coverage

11 tests covering: valid connect, expired token rejection, observe reads status, summarize appends, control denied (403), user_message filtered, invalid capability rejected, summary visible in events, unauthorized status (401), idempotent pairing, new pairing.
