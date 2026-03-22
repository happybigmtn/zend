# Zend Home Command Center — Specification

**Lane:** carried-forward-build-command-center
**Status:** Milestone 1 — partially implemented, not approved
**Generated:** 2026-03-19
**Last revised:** 2026-03-22

## Overview

This document specifies the first honest implementation slice of the Zend Home
Command Center: a private, mobile-first command surface for operating a home
Zcash miner from a paired phone. Mining does not happen on the phone. The phone
is the control plane only.

## Source Documents

This spec is grounded in:

- `DESIGN.md` — visual and interaction design system
- `PLANS.md` — rules for executable plans
- `plans/2026-03-19-build-zend-home-command-center.md` — live ExecPlan with
  architecture diagrams, error registry, and concrete validation steps
- `specs/2026-03-19-zend-product-spec.md` — accepted product boundary

## What Exists vs. What Is Planned

Implementation scaffolding is in place:

| Path | Exists | Status |
|------|--------|--------|
| `services/home-miner-daemon/` | ✓ | daemon.py, store.py, spine.py, cli.py |
| `apps/zend-home-gateway/` | ✓ | index.html (mobile-first HTML client) |
| `scripts/` | ✓ | 7 shell scripts (bootstrap, pair, status, mode, audit, etc.) |
| `references/` | ✓ | inbox-contract.md, event-spine.md, error-taxonomy.md, hermes-adapter.md, observability.md, design-checklist.md |
| `upstream/manifest.lock.json` | ✓ | Pinned upstream manifest |
| `plans/2026-03-19-build-zend-home-command-center.md` | ✓ | Live ExecPlan |
| `docs/designs/2026-03-19-zend-home-command-center.md` | ✓ | Product storyboard |
| `state/` | ✓ | Runtime state directory (gitignored) |

**Zero automated test files exist.** All testing is manual via scripts.

## Architecture

### Components

```
Thin Mobile Client
      |
      | pair + observe + control + inbox reads
      v
Zend Gateway Contract (apps/zend-home-gateway/index.html)
      |
      +--> Event Spine (services/home-miner-daemon/spine.py)
      +--> Pairing Store (services/home-miner-daemon/store.py)
      v
Home Miner Daemon (services/home-miner-daemon/daemon.py)
      |
      +--> Miner Simulator (in-process, thread-safe)
      +--> Hermes Adapter (contract only; not yet live)
```

The event spine is the append-only journal. The inbox is a derived projection
of spine events. The pairing store holds current capability state.

### Directory Layout

```
services/home-miner-daemon/
  daemon.py      — HTTP server, MinerSimulator, /health /status /miner/*
  cli.py         — command dispatch (bootstrap, pair, status, mode, audit)
  store.py       — pairing records, principal identity, token lifecycle
  spine.py       — append-only JSONL event journal

apps/zend-home-gateway/
  index.html     — mobile-first HTML command-center UI

scripts/
  bootstrap_home_miner.sh
  pair_gateway_client.sh
  read_miner_status.sh
  set_mining_mode.sh
  hermes_summary_smoke.sh
  no_local_hashing_audit.sh
  fetch_upstreams.sh

references/
  inbox-contract.md     — PrincipalId contract, pairing record shape
  event-spine.md        — EventKind taxonomy, spine as source of truth
  error-taxonomy.md     — named failure classes
  hermes-adapter.md     — Hermes delegation contract, observe-only M1
  observability.md      — structured log events and metrics
  design-checklist.md   — design system compliance checklist
```

## Data Models

### PrincipalId

```python
type PrincipalId = str  # UUID v4, stored in state/principal.json
```

Stable identity shared across gateway pairing records and future inbox access.
Created at bootstrap; never changed.

### GatewayCapability

```python
type GatewayCapability = "observe" | "control"
```

`observe` — read status, read inbox, receive summaries.
`control` — issue miner commands in addition to observe.

### MinerSnapshot

```python
class MinerSnapshot(NamedTuple):
    status: Literal["running", "stopped", "offline", "error"]
    mode:   Literal["paused", "balanced", "performance"]
    hashrate_hs: float
    temperature: float
    uptime_seconds: int
    freshness: str  # ISO 8601 UTC
```

Cached status returned by `GET /status`. Freshness is the timestamp at which
the snapshot was captured.

### EventKind

```python
type EventKind = (
    "pairing_requested"
  | "pairing_granted"
  | "capability_revoked"
  | "miner_alert"
  | "control_receipt"
  | "hermes_summary"
  | "user_message"
)
```

Every state-changing operation appends one or more events to the spine.

## Interfaces

### Daemon HTTP API

| Endpoint | Method | Auth required | Description |
|----------|--------|--------------|-------------|
| `/health` | GET | No | Returns `OK` |
| `/status` | GET | No | Returns `MinerSnapshot` |
| `/miner/start` | POST | No (M1 gap — see review) | Start miner |
| `/miner/stop` | POST | No (M1 gap — see review) | Stop miner |
| `/miner/set_mode` | POST | No (M1 gap — see review) | Set mode |

**M1 gap:** None of the mutating endpoints validate bearer tokens or capability
scopes. Authorization lives only in `cli.py`, not in the HTTP layer.

### CLI Commands

```bash
./scripts/bootstrap_home_miner.sh
  → starts daemon, creates PrincipalId, emits pairing token

./scripts/pair_gateway_client.sh --client <name> --capabilities observe,control
  → creates pairing record, appends spine events

./scripts/read_miner_status.sh --client <name>
  → reads and prints current MinerSnapshot

./scripts/set_mining_mode.sh --client <name> --mode <paused|balanced|performance>
  → issues control command, appends receipt to spine

./scripts/hermes_summary_smoke.sh --client <name>
  → appends a test HermesSummary event to spine

./scripts/no_local_hashing_audit.sh --client <name>
  → inspects client process tree; exits non-zero if hashing detected
```

## Security Properties (Intended vs. Actual)

| Property | Spec says | Implementation does |
|----------|-----------|---------------------|
| LAN-only binding | daemon binds loopback only | defaults to 127.0.0.1 but `ZEND_BIND_HOST=0.0.0.0` is accepted |
| Capability enforcement | control requires `control` capability | only enforced in `cli.py`, not in daemon HTTP |
| Event spine encryption | "append-only encrypted journal" | plaintext JSONL, no encryption |
| Pairing token lifecycle | tokens expire and are single-use | `token_expires_at` set to `now()` at creation; never checked |
| Trust ceremony | challenge-response pairing verification | `store.py:pair_client()` writes a JSON record; no ceremony |
| Command serialization | conflicting commands rejected | no serialization; concurrent requests both process |
| PrincipalId binding | cryptographically bound to identity | UUID in plaintext file; no key derivation |

## Known Gaps (from review)

1. **Daemon has no HTTP-layer authentication** — any process on localhost can
   issue `POST /miner/stop` without capability check.
2. **Spine is not encrypted** — events are plaintext JSONL.
3. **Token lifecycle is a no-op** — `token_expires_at` is always past; replay
   detection is absent.
4. **No trust ceremony** — pairing is a single JSON write, no verification step.
5. **No control serialization** — concurrent commands both succeed.
6. **`_started_at` never cleared on stop** — uptime counter grows while stopped.
7. **`ZEND_BIND_HOST` not validated** — `0.0.0.0` binding is accepted.
8. **Zero automated tests** — all verification is manual.
9. **`references/gateway-proof.md`** does not exist; required by ExecPlan.
10. **`references/onboarding-storyboard.md`** does not exist; required by ExecPlan.
11. **JSONL spine has no corruption recovery** — a partial write makes the spine
    unreadable.
12. **Gateway client hardcodes capabilities** — `index.html:626` always requests
    `['observe', 'control']` regardless of actual pairing.

## Out of Scope for Milestone 1

- Remote internet access (LAN-only is intentional)
- Payout-target mutation
- Rich conversation UX beyond operations inbox
- Hermes control authority (observe-only + summary append for M1)
- Encrypted spine (documented as a gap; encryption is M2+)
- Automated tests (documented as a gap; tests are M2+)

## Acceptance Criteria

These reflect the spec's intent, not the implementation's current state:

- [ ] Daemon binds only a loopback or link-local address in M1
- [ ] Pairing creates a stable PrincipalId and a capability-scoped record
- [ ] `GET /status` returns a MinerSnapshot with a real freshness timestamp
- [ ] Mutating endpoints enforce capability checks at the HTTP layer
- [ ] Events append to the spine atomically (no partial-write corruption)
- [ ] Inbox view shows receipts, alerts, and Hermes summaries as a projection
- [ ] Gateway client proves it performs no hashing on-device
- [ ] Trust ceremony involves a verification step beyond a single JSON write
- [ ] Conflicting control commands are detected and rejected
- [ ] Automated tests exist for all error taxonomy cases
- [ ] `references/gateway-proof.md` documents exact rerun transcripts
- [ ] Hermes connects only through the adapter contract with delegated authority
