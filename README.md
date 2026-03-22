# Zend

Zend is the private operating system for a household Zcash mining node. Pair one
trusted phone to one named home box, see live miner status, receive operational
receipts and Hermes agent summaries in one encrypted inbox — and prove that no
mining work happens on the phone.

**The phone is the control plane. The home miner is the workhorse. Mining does not
happen on-device.**

---

## Quickstart

### Prerequisites

- Python 3.10+
- a Unix-like shell (bash, zsh)
- one machine to run the home miner daemon
- one phone or browser to run the gateway client

### 1 — Bootstrap the daemon

```bash
cd /path/to/zend
./scripts/bootstrap_home_miner.sh
```

This starts the local miner simulator, creates a `PrincipalId`, and prints a
pairing token for `alice-phone`.

### 2 — Pair the gateway client

```bash
./scripts/pair_gateway_client.sh --client alice-phone
```

This records a paired client with `observe` and `control` capability. Open
`apps/zend-home-gateway/index.html` in a browser (or serve it from the same
host).

### 3 — Read live status

```bash
./scripts/read_miner_status.sh --client alice-phone
```

Returns current miner status, mode, hashrate, temperature, uptime, and a
freshness timestamp.

### 4 — Control the miner

```bash
./scripts/set_mining_mode.sh --client alice-phone --mode balanced
```

Requires `control` capability. Prints an explicit acknowledgement that the home
miner accepted the command.

### 5 — Prove no local hashing

```bash
./scripts/no_local_hashing_audit.sh --client alice-phone
```

Exits non-zero if the gateway client process tree shows hashing work. This is
the off-device proof.

---

## Architecture Overview

```
Thin Mobile Client
       |
       | pair + observe + control + inbox
       v
Zend Gateway Contract
    |           |
    |           +--> Zend Event Spine
    v
Home Miner Daemon
    |        |
    |        +--> Hermes Adapter --> Hermes Gateway
    +--> Miner backend or simulator
              |
              v
         Zcash network
```

**Key invariants:**

- The daemon binds LAN-only (`127.0.0.1`) in milestone 1.
- The event spine is the source of truth; the inbox is a derived view.
- A single `PrincipalId` governs both gateway pairing and future inbox access.
- Gateway permissions are scoped to `observe` or `control` only.
- Mining work never runs on the client device.

### Modules

| Module | Location | Purpose |
|--------|----------|---------|
| Home Miner Daemon | `services/home-miner-daemon/` | LAN-only control service exposing safe status and control endpoints |
| Gateway Client | `apps/zend-home-gateway/` | Mobile-first web UI (four-tab: Home, Inbox, Agent, Device) |
| Event Spine | `references/event-spine.md` | Append-only encrypted journal; single source of truth |
| Inbox Contract | `references/inbox-contract.md` | `PrincipalId` and pairing record definitions |
| Hermes Adapter | `references/hermes-adapter.md` | Zend-native bridge to Hermes Gateway |
| Error Taxonomy | `references/error-taxonomy.md` | Named error classes for all failure modes |
| Observability | `references/observability.md` | Structured log events and metrics |
| Design System | `DESIGN.md` | Typography, color, component vocabulary, AI-slop guardrails |

### Scripts

| Script | Purpose |
|--------|---------|
| `bootstrap_home_miner.sh` | Start daemon, create `PrincipalId`, register first device |
| `pair_gateway_client.sh` | Register a paired client via CLI |
| `read_miner_status.sh` | Return `MinerSnapshot` via CLI |
| `set_mining_mode.sh` | Safe control action via CLI; checks capability |
| `hermes_summary_smoke.sh` | Prove Hermes adapter can append a summary |
| `no_local_hashing_audit.sh` | Prove client process tree contains no hashing |
| `fetch_upstreams.sh` | Clone/refresh pinned upstream repos |

The CLI (`services/home-miner-daemon/cli.py`) wraps the daemon HTTP API with
capability checks and event-spine operations. Scripts call the CLI, not raw HTTP.

---

## Current Scope

This repository contains the canonical planning documents and the first
implementation slice for Zend Home. The first slice includes:

- a home-miner daemon (simulator-backed for milestone 1)
- a thin mobile-shaped gateway client
- a trust ceremony with explicit capability grants
- an encrypted operations inbox fed by one private event spine
- a Zend-native gateway contract with a Hermes adapter
- LAN-only pairing and control

Not yet in scope: remote internet access, payout-target mutation, rich
conversation UX, and real miner backend integration. See `TODOS.md` for the full
deferred-work register.

---

## Repository Structure

```
README.md                  ← you are here
SPEC.md                    ← how to write durable specs
PLANS.md                  ← how to author executable plans
DESIGN.md                 ← visual and interaction design system
TODOS.md                  ← deliberate deferrals
plans/                    ← live ExecPlans
specs/                    ← durable decision/capability specs
apps/zend-home-gateway/  ← thin mobile client
services/                 ← daemon and control service
scripts/                  ← operator and proof scripts
references/               ← contracts and architecture notes
upstream/                 ← pinned external dependencies
state/                    ← local runtime data (ignored by git)
outputs/                  ← lane review artifacts
```

## Contributing

See `docs/contributor-guide.md` for development setup, testing, and code
conventions.
