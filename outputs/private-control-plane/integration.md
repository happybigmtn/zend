# Private Control Plane — Integration

**Status:** Authenticated daemon integration
**Generated:** 2026-03-20
**Updated:** 2026-03-20 (pairing-token flow)

## Integration Summary

The private control plane now integrates as an authenticated chain instead of a trusted local shortcut:

```text
paired device record
    -> shared CLI
    -> Authorization: Bearer <auth_token>
    -> home-miner daemon capability gate
    -> miner simulator
    -> event spine
```

This preserves the reviewed lane doctrine that pairing authority and spine events share the same `PrincipalId`, while closing the gap where raw daemon HTTP could bypass capability checks.

## Component Responsibilities

### Pairing Store

- Owns `PrincipalId`, device name, capabilities, `auth_token`, and `token_expires_at`
- Migrates legacy records missing a durable bearer token
- Resolves bearer token to device record for daemon authorization

### Shared CLI

- Loads the local paired device by name
- Rejects expired pairings before making a daemon call
- Enforces capability expectations for `observe` and `control`
- Adds the bearer token to outbound daemon requests

### Home Miner Daemon

- Leaves `/health` open for local liveness checks
- Requires bearer auth on `/status`, `/spine/events`, and `/miner/*`
- Re-checks the requested capability at the HTTP boundary
- Returns named authorization errors instead of accepting anonymous control

### Event Spine

- Remains the only operational event log
- Receives `control_receipt` after successful or rejected control attempts through the CLI flow

## Capability Matrix

| Client type | `GET /status` | `GET /spine/events` | `POST /miner/set_mode` |
|-------------|---------------|---------------------|------------------------|
| no token | reject | reject | reject |
| observe token | allow | allow | reject |
| control token | allow | allow | allow |

## Bootstrap and Pairing Flow

```text
bootstrap_home_miner.sh
    -> cli.py bootstrap
    -> principal + observe pairing
    -> pairing_token emitted for alice-phone

pair_gateway_client.sh --client bob-phone --capabilities observe,control
    -> cli.py pair
    -> pairing record persisted
    -> pairing_requested + pairing_granted appended to spine
    -> pairing_token emitted for bob-phone
```

## Control Flow

```text
set_mining_mode.sh --client bob-phone --mode balanced
    -> cli.py loads bob pairing
    -> CLI confirms `control`
    -> daemon receives Bearer token
    -> daemon confirms token + `control`
    -> miner mode changes
    -> control_receipt appended to spine
```

Observe-only control attempts fail before the daemon call at the shared CLI layer and would also fail at the daemon boundary if a raw HTTP client tried to reuse that observe token.

## Operational Notes

- This slice keeps the existing LAN-only binding and daemon lifecycle behavior.
- The live network proof from earlier slices still covers startup/bind behavior; this slice primarily changes auth and request routing.
- Hermes integration, inbox encryption, and revocation flows stay outside this slice.
