# Zend Home Command Center — Specification

**Status:** Milestone 1 Implementation
**Source:** `plans/2026-03-19-build-zend-home-command-center.md`
**Governing design:** `DESIGN.md` | **Governing product spec:** `specs/2026-03-19-zend-product-spec.md`

---

## What This Artifact Is

This file is the durable specification for the first honest reviewed slice of the
Zend Home Command Center. It is derived from the ExecPlan in
`plans/2026-03-19-build-zend-home-command-center.md` and the accepted product
boundary in `specs/2026-03-19-zend-product-spec.md`.

It is **not** a plan. It does not describe implementation steps. It describes
the durable target: what the system must do, what it must not do, and how the
parts relate to each other.

---

## Purpose / User-Visible Outcome

A person or agent can pair a thin mobile-shaped command center to a home miner
running on the same LAN, read live miner status, change safe operating modes
(paused / balanced / performance), and receive all operational events — pairing
receipts, control acknowledgements, Hermes summaries, and alerts — in one
encrypted operations inbox.

The phone never mines. The home miner does all hashing work. The command center
proves this with an audit script that inspects the client process tree and fails
if any hashing work is detected.

---

## Scope

### In Scope for Milestone 1

| Concern | Implementation |
|---------|----------------|
| Mobile command center into home miner | `apps/zend-home-gateway/index.html` |
| LAN-only daemon with `/health`, `/status`, `/miner/*` | `services/home-miner-daemon/daemon.py` |
| Shared `PrincipalId` contract (UUID v4) | `services/home-miner-daemon/store.py` |
| Capability-scoped pairing (`observe` / `control`) | `services/home-miner-daemon/store.py` |
| Miner simulator with cached `MinerSnapshot` | `services/home-miner-daemon/daemon.py` |
| Encrypted operations inbox (derived view of event spine) | `services/home-miner-daemon/spine.py` |
| Append-only event spine with 7 event kinds | `references/event-spine.md` |
| Hermes adapter contract | `references/hermes-adapter.md` |
| Inbox contract (shared `PrincipalId`) | `references/inbox-contract.md` |
| Error taxonomy (10 named error classes) | `references/error-taxonomy.md` |
| Observability events and metrics | `references/observability.md` |
| Design checklist | `references/design-checklist.md` |
| Bootstrap, pair, status, mode, Hermes, audit scripts | `scripts/*.sh` |
| Pinned upstream manifest | `upstream/manifest.lock.json` |
| Off-device mining proof (audit stub) | `scripts/no_local_hashing_audit.sh` |

### Explicitly Out of Scope

- Remote internet access to the daemon (LAN-only, permanent for this slice)
- Payout-target mutation
- Real Hermes integration (contract defined only)
- Rich inbox UX beyond raw event rendering
- Persistence tests, integration tests, automated tests
- Accessibility verification
- Real miner backend (simulator used)

---

## Architecture

### Components and Their Locations

```
scripts/
  bootstrap_home_miner.sh       — start daemon, create PrincipalId
  pair_gateway_client.sh        — create pairing record with capability
  read_miner_status.sh          — fetch MinerSnapshot from daemon
  set_mining_mode.sh            — POST miner control, check capability
  hermes_summary_smoke.sh       — append Hermes summary to spine
  no_local_hashing_audit.sh     — prove client does no hashing
  fetch_upstreams.sh            — clone/update pinned upstreams

services/home-miner-daemon/
  daemon.py     — HTTP server: /health, /status, /miner/start|stop|set_mode
  store.py      — PrincipalId and pairing record CRUD
  spine.py      — append-only event spine and query
  cli.py        — CLI entry point for daemon and scripts
  __init__.py   — package marker

apps/zend-home-gateway/
  index.html    — mobile-first four-tab command center (Home, Inbox, Agent, Device)

references/
  event-spine.md        — event kinds, schema, routing rules
  inbox-contract.md     — PrincipalId, pairing record, inbox metadata
  hermes-adapter.md     — Hermes adapter interface and authority scope
  error-taxonomy.md     — 10 named error classes with user messages
  observability.md      — structured log events and metrics
  design-checklist.md   — implementation-ready design checklist
```

### Network Binding

The daemon binds to `127.0.0.1:8080` in milestone 1. This is the LAN-only
commitment. The binding is hardcoded in `services/home-miner-daemon/daemon.py`
and is not configurable in this slice.

### Data Models

#### PrincipalId

```python
PrincipalId = str  # UUID v4
```

Created by `store.py` during `bootstrap_home_miner.sh`. Referenced by all
pairing records, all event-spine items, and all future inbox metadata.

#### GatewayCapability

```python
GatewayCapability = Literal["observe", "control"]
```

#### MinerSnapshot

```python
@dataclass
class MinerSnapshot:
    status: Literal["running", "stopped", "offline", "error"]
    mode: Literal["paused", "balanced", "performance"]
    hashrate_hs: float
    temperature: float
    uptime_seconds: int
    freshness: str  # ISO 8601
```

Returned by `GET /status`. Cached by the daemon from the miner simulator.

#### EventKind

```python
EventKind = Literal[
    "pairing_requested",
    "pairing_granted",
    "capability_revoked",
    "miner_alert",
    "control_receipt",
    "hermes_summary",
    "user_message",
]
```

Defined in `references/event-spine.md`. All events are written to the spine first;
the inbox is a derived view.

---

## Interfaces

### Daemon HTTP API

| Endpoint | Method | Auth Required | Description |
|----------|--------|---------------|-------------|
| `/health` | GET | None | Liveness probe |
| `/status` | GET | `observe` | Cached `MinerSnapshot` |
| `/miner/start` | POST | `control` | Start mining |
| `/miner/stop` | POST | `control` | Stop mining |
| `/miner/set_mode` | POST | `control` | Set `paused`/`balanced`/`performance` |

All endpoints return JSON. Error responses carry a named `error_code` field from
`references/error-taxonomy.md`.

### CLI Interface

```bash
# Bootstrap daemon + create principal
./scripts/bootstrap_home_miner.sh

# Pair a client
./scripts/pair_gateway_client.sh --client alice-phone --capabilities observe,control

# Read status
./scripts/read_miner_status.sh --client alice-phone

# Control miner
./scripts/set_mining_mode.sh --client alice-phone --mode balanced
./scripts/set_mining_mode.sh --client alice-phone --action start
./scripts/set_mining_mode.sh --client alice-phone --action stop

# Hermes summary smoke test
./scripts/hermes_summary_smoke.sh --client alice-phone

# Off-device mining proof
./scripts/no_local_hashing_audit.sh --client alice-phone
```

All scripts exit non-zero on failure and print structured output or a named
error code.

---

## Security Properties

| Property | Enforcement | Location |
|----------|-------------|----------|
| LAN-only daemon binding | Hardcoded `127.0.0.1` | `daemon.py` |
| Capability-scoped control | `store.py` checks before daemon call | `cli.py` |
| Off-device mining | Simulator; audit stub | `daemon.py`, `no_local_hashing_audit.sh` |
| Event spine append-only | `spine.py` only appends, never modifies | `spine.py` |
| Spine is source of truth | Inbox is derived view | `spine.py`, `inbox-contract.md` |

---

## Out-of-Scope Boundary (Permanent for This Slice)

The following are not deferred — they are permanently excluded from milestone 1:

- **Remote access:** The daemon does not expose any internet-facing control surface.
- **Payout mutation:** The daemon does not expose any endpoint that changes where
  mining rewards are sent.
- **Real Hermes connection:** The adapter contract is defined but no live Hermes
  gateway is connected.
- **Event compaction:** The spine appends forever with no archival or pruning.

---

## Acceptance Criteria

Each criterion maps to evidence a human or agent can observe without reading source
code.

| # | Criterion | Evidence |
|---|-----------|----------|
| 1 | Daemon starts and binds localhost | `curl http://127.0.0.1:8080/health` returns `200 OK` |
| 2 | Pairing creates `PrincipalId` | `scripts/pair_gateway_client.sh --client bob-phone` succeeds; `state/` contains a UUID |
| 3 | `observe`-only client cannot control | `set_mining_mode.sh` with observe-only client returns `GATEWAY_UNAUTHORIZED` |
| 4 | Status returns `MinerSnapshot` | `scripts/read_miner_status.sh` output includes `status`, `mode`, `freshness` |
| 5 | Control appends a receipt to the spine | `spine.py` event log grows after `set_mining_mode.sh` |
| 6 | Hermes summary appends to spine | `scripts/hermes_summary_smoke.sh` appends a `hermes_summary` event |
| 7 | Audit proves no local hashing | `scripts/no_local_hashing_audit.sh` exits `0` on a clean client |
| 8 | Event spine is source of truth | `references/event-spine.md` is the only write path; inbox has no independent write API |

---

## Relationship to Other Documents

| Document | Role |
|----------|------|
| `specs/2026-03-19-zend-product-spec.md` | Durable product boundary — this spec implements the milestone 1 slice of that spec |
| `plans/2026-03-19-build-zend-home-command-center.md` | Executable plan — the living document that tracked what was built and how |
| `DESIGN.md` | Visual and interaction design system — governs all `apps/zend-home-gateway/` UI decisions |
| `references/event-spine.md` | Contract for the append-only journal |
| `references/inbox-contract.md` | Contract for `PrincipalId` and pairing |
| `references/error-taxonomy.md` | Named error classes and user-facing messages |
| `references/hermes-adapter.md` | Hermes adapter interface and authority boundaries |
| `references/observability.md` | Structured log events and metrics |
| `references/design-checklist.md` | Implementation-ready design checklist |
