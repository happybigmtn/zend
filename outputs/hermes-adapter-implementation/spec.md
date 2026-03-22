# Hermes Adapter Implementation — Spec

Status: Implemented (pending review fixes)
Lane: hermes-adapter-implementation

## What Was Built

A Hermes adapter module (hermes.py) that enforces a capability-scoped boundary for
AI agent access to the Zend home miner daemon. The adapter mediates all Hermes
interactions with the system, ensuring agents can only observe miner status and
append summaries — never issue control commands or read user messages.

## Files

- services/home-miner-daemon/hermes.py: Core adapter module
- services/home-miner-daemon/daemon.py: HTTP endpoint integration
- services/home-miner-daemon/cli.py: CLI command surface for Hermes operations
- services/home-miner-daemon/tests/test_hermes.py: 20 unit tests

## Capabilities Implemented

1. HermesConnection with authority token validation (base64 JSON tokens with
   hermes_id, principal_id, capabilities, expiration)
2. readStatus through adapter (observe capability required, payload transformation)
3. appendSummary through adapter (summarize capability required, writes to event spine)
4. Event filtering (user_message events blocked, control_receipt payloads stripped)
5. Hermes pairing endpoint (idempotent, LAN-only)
6. CLI commands: hermes pair, hermes status, hermes summary, hermes events

## Capability Model

Hermes agents are limited to two capabilities: observe and summarize. The
capability allowlist is enforced at three levels:

1. Token parse time: unknown capabilities rejected
2. Adapter function level: each operation checks for its required capability
3. HTTP handler level: control endpoints check for Hermes header and block

## Test Results

20/20 tests passing. Coverage includes token lifecycle, capability enforcement,
event filtering, pairing idempotence, and control blocking.

## Known Limitations (LAN-only M1)

- Authority token is validated on connect but not on subsequent requests
- Pairing endpoint has no authentication
- File-based stores are not atomic
- Token expiration on pairing is incorrectly set to current time (blocker B3)
- Hermes principal management diverges from store.py (blocker B4)

See review.md for the full blocker list and recommended fixes.
