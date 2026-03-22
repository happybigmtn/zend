# Zend

Zend is a private command center for a home miner. The phone or script is the
control plane — mining happens on hardware you control, not on the device in
your hand.

Encrypted Zcash-family memo transport carries messages and operational receipts.
No chain fork, no on-device mining, no public feeds.

## What This Repository Is

This is the canonical planning and implementation repository for Zend. It contains:

- **`specs/`** — durable product and architecture specs
- **`plans/`** — executable implementation plans (ExecPlans) that a coding agent
  can follow from a fresh clone
- **`services/`** — the home-miner daemon (LAN-only HTTP control service)
- **`apps/`** — the gateway client (mobile-shaped HTML + JS, no build step)
- **`scripts/`** — operator and developer scripts
- **`DESIGN.md`** — visual and interaction design system

## Quickstart

Prerequisites: Python 3. No other dependencies.

```bash
# 1. Start the daemon and bootstrap principal identity
./scripts/bootstrap_home_miner.sh

# 2. Pair a gateway client (observe + control capabilities)
./scripts/pair_gateway_client.sh --client alice-phone --capabilities observe,control

# 3. Read live miner status
./scripts/read_miner_status.sh --client alice-phone

# 4. Change mining mode
./scripts/set_mining_mode.sh --client alice-phone --mode balanced

# 5. Open the gateway UI
open apps/zend-home-gateway/index.html
# Or serve it: python3 -m http.server 9000 --directory apps/zend-home-gateway
```

The daemon binds to `127.0.0.1:8080` by default. Set `ZEND_BIND_HOST` and
`ZEND_BIND_PORT` to expose on a LAN interface (e.g. `192.168.1.x`).

## Architecture Overview

```
  Gateway Client (phone/browser)
         |  observe + control
         v
  Zend Home Miner Daemon          Hermes Adapter
  (LAN HTTP, no auth)  ----------> Hermes Gateway
         |
         +--> Miner Simulator (milestone 1)
         |         or
         +--> Real miner backend (future)
         |
         v
  Event Spine (append-only JSONL, plaintext in milestone 1)
         ^
         |  projections
  Operations Inbox  <--  Pairing receipts, control receipts,
                           alerts, Hermes summaries
```

### Daemon (`services/home-miner-daemon/`)

- **`daemon.py`** — LAN-only HTTP server. Endpoints: `GET /health`,
  `GET /status`, `POST /miner/start`, `POST /miner/stop`,
  `POST /miner/set_mode`. Uses a `MinerSimulator` in milestone 1.
- **`cli.py`** — CLI with `bootstrap`, `pair`, `status`, `control`,
  `events` subcommands. Enforces `observe`/`control` capability checks.
- **`store.py`** — Principal and pairing store. `PrincipalId` is the stable
  user identity; `GatewayPairing` records carry capability lists.
- **`spine.py`** — Append-only event journal. Event kinds:
  `pairing_requested`, `pairing_granted`, `capability_revoked`,
  `miner_alert`, `control_receipt`, `hermes_summary`, `user_message`.

### Gateway Client (`apps/zend-home-gateway/`)

Single HTML file. No build step. Four destinations: **Home** (status hero +
mode switcher), **Inbox** (receipts and messages), **Agent** (Hermes status),
**Device** (pairing and permissions). Uses Space Grotesk + IBM Plex Sans +
IBM Plex Mono per `DESIGN.md`.

### Scripts (`scripts/`)

| Script | Purpose |
|--------|---------|
| `bootstrap_home_miner.sh` | Start daemon + create principal + emit pairing bundle |
| `pair_gateway_client.sh` | Pair a named client with specified capabilities |
| `read_miner_status.sh` | Read current miner status and snapshot freshness |
| `set_mining_mode.sh` | Issue a control action (start/stop/set_mode) |
| `hermes_summary_smoke.sh` | Append a Hermes summary to the event spine |
| `no_local_hashing_audit.sh` | Verify the client performs no local hashing |

## Key Facts

- **No authentication on the daemon.** The HTTP server accepts all requests.
  LAN-only binding is the only access control in milestone 1.
- **Event spine is plaintext.** `state/event-spine.jsonl` is plain JSONL.
  The spec calls it encrypted; the implementation does not encrypt it yet.
- **Pairing tokens never expire.** `store.py` sets expiration to `now`.
- **Capability enforcement is at the CLI layer only.** Bypassing `cli.py`
  with `curl` skips all capability checks.
- **This is milestone 1.** Not production-ready. See `docs/operator-quickstart.md`
  for known limitations and deployment guidance.

## Learning More

- **Product spec:** `specs/2026-03-19-zend-product-spec.md`
- **Implementation plan:** `plans/2026-03-19-build-zend-home-command-center.md`
- **Design system:** `DESIGN.md`
- **Contributor guide:** `docs/contributor-guide.md`
- **Operator quickstart:** `docs/operator-quickstart.md`
- **API reference:** `docs/api-reference.md`
- **Architecture deep-dive:** `docs/architecture.md`
