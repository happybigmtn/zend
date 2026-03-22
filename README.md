# Zend

`Zend` is the canonical planning repository for an agent-first product that
combines encrypted Zcash-based messaging with a mobile gateway into a home miner.

The durable product decision locked in here is simple: the phone is the control
plane and the home miner is the workhorse. Mining does not happen on-device.
Encrypted messaging continues to rely on shielded Zcash-family memo transport.

## Quickstart

```bash
# 1. Bootstrap the daemon and principal identity
./scripts/bootstrap_home_miner.sh

# 2. Pair a client (observe-only by default)
./scripts/pair_gateway_client.sh --client alice-phone

# 3. Read live miner status
./scripts/read_miner_status.sh --client alice-phone

# 4. Change mining mode (requires --capabilities observe,control on pair)
./scripts/set_mining_mode.sh --client alice-phone --mode balanced

# 5. View the encrypted operations inbox (event spine)
cd services/home-miner-daemon && python3 cli.py events --client alice-phone

# 6. Stop the daemon
./scripts/bootstrap_home_miner.sh --stop
```

## Architecture Overview

```
  ┌──────────────────────────────────────────────────────┐
  │                   Zend Home Product                   │
  ├──────────────────────────────────────────────────────┤
  │                                                      │
  │   Mobile / Script Client                             │
  │   (alice-phone, hermes-agent, etc.)                  │
  │            │                                         │
  │            │ HTTP: status, start, stop, set_mode     │
  │            │ CLI:  pair, control, events              │
  │            ▼                                         │
  │   services/home-miner-daemon/                        │
  │   ┌─────────────────────────────────────────────┐   │
  │   │  daemon.py   — HTTP API (LAN-only, no auth) │   │
  │   │  cli.py      — CLI with capability checks    │   │
  │   │  store.py    — Principal + pairing records   │   │
  │   │  spine.py    — Append-only event journal     │   │
  │   └─────────────────────────────────────────────┘   │
  │            │                                         │
  │            │ Miner simulator (same process)           │
  │            ▼                                         │
  │   state/                                           │
  │   ├── principal.json       ← shared identity         │
  │   ├── pairing-store.json  ← device + capabilities   │
  │   ├── event-spine.jsonl   ← all operational events   │
  │   └── daemon.pid           ← runtime PID             │
  │                                                      │
  └──────────────────────────────────────────────────────┘
```

### Key Modules

| File | Role |
|---|---|
| `services/home-miner-daemon/daemon.py` | LAN-only HTTP server. Exposes `/health`, `/status`, `/miner/start`, `/miner/stop`, `/miner/set_mode`. **No authentication.** |
| `services/home-miner-daemon/cli.py` | CLI wrapper around the daemon. Enforces `observe`/`control` capability checks. Commands: `bootstrap`, `pair`, `status`, `control`, `events`. |
| `services/home-miner-daemon/store.py` | Principal identity store and pairing records. Manages `principal.json` and `pairing-store.json`. |
| `services/home-miner-daemon/spine.py` | Append-only event journal. Feeds the operations inbox. **Plaintext JSONL — not encrypted.** |
| `scripts/bootstrap_home_miner.sh` | Starts the daemon, creates principal, emits pairing info. |
| `scripts/pair_gateway_client.sh` | Pairs a named client with `observe` or `observe,control` capability. |
| `scripts/read_miner_status.sh` | Reads a fresh `MinerSnapshot` from the daemon. |
| `scripts/set_mining_mode.sh` | Issues a safe control action to the home miner. |
| `scripts/hermes_summary_smoke.sh` | Appends a Hermes summary event into the spine. |
| `scripts/no_local_hashing_audit.sh` | Verifies the client performs no hashing work. |

### Security Posture (Milestone 1)

> **Important:** The HTTP daemon has **no authentication**. Any process that can
> reach the daemon's bound address can start, stop, or reconfigure the miner.
> The capability model (`observe`/`control`) is enforced only in the CLI layer,
> not in the daemon itself.

- Default bind: `127.0.0.1` (local only). Setting `ZEND_BIND_HOST=0.0.0.0`
  exposes an unauthenticated control surface to the LAN.
- Pairing tokens have zero TTL (expire at creation). No cryptographic validation.
- Event spine is plaintext JSONL. Not encrypted.
- No replay protection on control commands.
- State directory uses default umask permissions.

See `docs/operator-quickstart.md` for operational security guidance and
`docs/architecture.md` for the full system contract.

## Canonical Documents

- `SPEC.md` — guide for durable specs
- `PLANS.md` — guide for executable implementation plans
- `DESIGN.md` — visual and interaction design system
- `specs/2026-03-19-zend-product-spec.md` — accepted product capability spec
- `plans/2026-03-19-build-zend-home-command-center.md` — current ExecPlan
- `docs/designs/2026-03-19-zend-home-command-center.md` — product storyboard
- `TODOS.md` — deliberate deferrals with context

## Current Scope

The first implementation slice is the smallest real Zend product: a thin
mobile-shaped command center, a LAN-paired home miner, a Zend-native gateway
contract, and an encrypted operations inbox backed by a private event spine.

This repository does not yet contain the mobile app UI or a real miner backend.
The daemon ships with a milestone-1 simulator that exposes the same contract a
real miner will use.
