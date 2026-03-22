# Documentation & Onboarding — Spec

**Status:** Complete
**Lane:** `documentation-and-onboarding`
**Date:** 2026-03-22

## Purpose

Produce a complete, accurate, and tested documentation suite that enables:
- A new contributor to set up a dev environment and run the test suite from scratch
- An operator to deploy Zend on home hardware and operate it daily
- An API consumer to integrate against the daemon with working curl examples
- A new engineer to understand the system architecture and predict implementation patterns

## Scope

### Inputs
- `README.md` — high-level intro, no practical quickstart
- `SPEC.md` — spec writing guide
- `SPECS.md` — spec types (decision, migration, capability)
- `PLANS.md` — exec plan authoring rules
- `DESIGN.md` — visual and interaction system
- `genesis/plans/001-master-plan.md` — (not present, skipped)

### Outputs (this lane)

| File | Purpose |
|------|---------|
| `README.md` (rewrite) | Gateway document: what Zend is, quickstart, architecture diagram, directory structure |
| `docs/contributor-guide.md` | Dev environment setup, project structure, making changes, coding conventions |
| `docs/operator-quickstart.md` | Home hardware deployment, first boot, daily operations, recovery |
| `docs/api-reference.md` | Every daemon endpoint with curl examples |
| `docs/architecture.md` | System diagrams, module guide, data flow, auth model, design decisions |
| `outputs/documentation-and-onboarding/review.md` | Honest assessment of completeness and accuracy |

## Design Decisions

1. **Docs live in `docs/`** — Docs travel with code. No wiki, no external site.
2. **README is a gateway, not a manual** — Under 200 lines. Details in `docs/`.
3. **API reference curl examples must work** — Every example is verified against a running daemon.
4. **Architecture doc enables prediction** — An engineer who reads it should accurately predict how a new endpoint would be implemented.

## Acceptance Criteria

- [x] README quickstart works from a fresh clone
- [x] Contributor guide enables test suite execution without tribal knowledge
- [x] Operator guide covers full deployment lifecycle on home hardware
- [x] API reference curl examples all work against running daemon
- [x] Architecture doc correctly describes the current system
- [x] Verification performed by running the quickstart end-to-end

## System Understanding

### What Zend Is

Zend is a private command center that pairs a mobile gateway with a home miner. The phone is the control plane; the home miner is the workhorse. Mining never happens on the phone.

### Architecture

```
  ┌─────────────────────────────────────────────┐
  │   apps/zend-home-gateway/index.html        │
  │   (mobile command center, single HTML file) │
  └──────────────────────┬────────────────────┘
                         │ HTTP / observe + control
                         ▼
  ┌─────────────────────────────────────────────┐
  │   services/home-miner-daemon/daemon.py     │
  │   (LAN-only HTTP server, Python stdlib)    │
  │                                              │
  │   GET  /health                              │
  │   GET  /status                              │
  │   POST /miner/start                         │
  │   POST /miner/stop                          │
  │   POST /miner/set_mode                      │
  └──────┬──────────────────┬───────────────────┘
         │                  │
         ▼                  ▼
  ┌─────────────┐   ┌──────────────────────────┐
  │ spine.py    │   │ store.py                 │
  │ (event     │   │ (principal + pairing      │
  │  spine,    │   │  records, JSON files)     │
  │  JSONL)    │   └──────────────────────────┘
  └─────────────┘

  Shell scripts wrap the CLI:
    scripts/bootstrap_home_miner.sh
    scripts/pair_gateway_client.sh
    scripts/read_miner_status.sh
    scripts/set_mining_mode.sh
```

### Key Modules

| Module | Purpose | State |
|--------|---------|-------|
| `daemon.py` | HTTP API server, miner simulator | In-memory + JSON files |
| `cli.py` | Command-line interface | Imports store, spine |
| `spine.py` | Append-only event journal (JSONL) | `state/event-spine.jsonl` |
| `store.py` | Principal + pairing records | `state/principal.json`, `state/pairing-store.json` |

### Capabilities

- **`observe`** — Read miner status and events
- **`control`** — Start, stop, or change miner mode

### Miner Modes

- **`paused`** — No mining
- **`balanced`** — 50 kH/s simulated hashrate
- **`performance`** — 150 kH/s simulated hashrate

### State Files

All state lives under `state/` (gitignored):

| File | Contents |
|------|----------|
| `principal.json` | PrincipalId and creation timestamp |
| `pairing-store.json` | All paired devices and their capabilities |
| `event-spine.jsonl` | Append-only event log |
| `daemon.pid` | Running daemon PID |

## Verification

The quickstart was verified by:
1. Running `bootstrap_home_miner.sh` from a fresh state
2. Confirming daemon health check returns `{"healthy": true}`
3. Confirming `cli.py status` returns miner snapshot
4. Confirming mode change via `cli.py control --action set_mode --mode balanced`
5. Confirming event append to spine via `cli.py events`
6. Confirming HTML gateway fetches `/status` and renders correctly
