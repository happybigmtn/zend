# Private Control Plane — Implementation

**Status:** Authenticated pairing slice complete
**Generated:** 2026-03-20
**Updated:** 2026-03-20 (daemon auth enforcement)

## Slice Summary

This slice makes capability-scoped pairing real on the daemon surface. The home-miner daemon now requires a paired device bearer token for `observe` and `control` routes, the shared CLI forwards that token on every authorized request, and legacy pairings are migrated forward so existing local state keeps working.

## Touched Surfaces

```text
services/home-miner-daemon/store.py
services/home-miner-daemon/cli.py
services/home-miner-daemon/daemon.py
scripts/bootstrap_home_miner.sh
scripts/pair_gateway_client.sh
scripts/set_mining_mode.sh
```

## Pairing Credential Model

`GatewayPairing` now persists a durable `auth_token` alongside `token_expires_at`.

```python
@dataclass
class GatewayPairing:
    id: str
    principal_id: str
    device_name: str
    capabilities: list
    paired_at: str
    token_expires_at: str
    auth_token: str = ""
    token_used: bool = False
```

Implementation details:

- `store.py:create_pairing_token()` issues a UUID bearer token with a 30-day TTL.
- `store.py:load_pairings()` normalizes old records that were missing `auth_token` or carried the old immediate-expiry bug.
- `store.py:get_pairing_by_token()` lets the daemon resolve incoming bearer tokens back to paired devices.
- `store.py:pairing_token_expired()` is used by both the CLI and the daemon so expiry checks stay consistent.

## Auth Flow

The request path for an authenticated client is now:

1. `bootstrap_home_miner.sh` or `pair_gateway_client.sh` creates or reuses a paired device record.
2. The CLI loads that device's pairing, checks expiry and capability, then calls the daemon with `Authorization: Bearer <auth_token>`.
3. `daemon.py:GatewayHandler._authorize()` re-validates the bearer token and required capability before exposing status, event, or control routes.
4. Successful control requests still append a `control_receipt` to the event spine, keeping the spine as the source of truth.

## Route Enforcement

| Route | Capability | Behavior |
|-------|------------|----------|
| `GET /health` | none | Remains open for local liveness checks |
| `GET /status` | `observe` or `control` | Rejects missing, invalid, or expired tokens |
| `GET /spine/events` | `observe` or `control` | Rejects missing, invalid, or expired tokens |
| `POST /miner/start` | `control` | Rejects observe-only tokens |
| `POST /miner/stop` | `control` | Rejects observe-only tokens |
| `POST /miner/set_mode` | `control` | Rejects observe-only tokens |

Returned named errors now align with the repo taxonomy:

- `GATEWAY_UNAUTHORIZED` for missing or insufficient authority
- `PAIRING_TOKEN_EXPIRED` for expired device credentials
- `GATEWAY_UNAVAILABLE` for daemon transport failures surfaced by the CLI

## Shared Client Behavior

The shell scripts remain thin wrappers over the shared CLI:

- `bootstrap_home_miner.sh` now prints the bootstrap device's `pairing_token` so later steps can reuse it.
- `pair_gateway_client.sh` prints the current token for both fresh and idempotent pairings.
- `set_mining_mode.sh` recognizes `GATEWAY_UNAUTHORIZED` and `PAIRING_TOKEN_EXPIRED` responses from the CLI.

No shell script duplicates auth rules. Capability checks and bearer-token propagation stay centralized in `cli.py`.

## Event Spine Behavior

This slice does not introduce any second event store. Control actions still flow:

```text
paired client -> CLI auth check -> daemon auth check -> miner action -> spine.append_control_receipt()
```

That keeps the reviewed control-plane doctrine intact:

- one stable `PrincipalId`
- one pairing model
- one event spine as the source of truth

## Slice Boundaries

The following items remain outside this implementation slice:

- capability revocation workflow
- distributed conflict handling beyond the in-process miner lock
- Hermes delegated auth
- encrypted event payload transport

Those boundaries are unchanged by this patch; the delivered work is the secure pairing/auth layer for the daemon routes already owned by `private-control-plane`.
