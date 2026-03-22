# Documentation & Onboarding — Specification

**Status:** Complete
**Date:** 2026-03-22
**Lane:** `documentation-and-onboarding`

## Purpose

Bootstrap a reviewed, accurate documentation set so that a newcomer can go from a fresh clone to a working Zend system in under 10 minutes, and an operator can deploy on home hardware, following only the documentation.

## What Was Produced

### Durable Artifacts

| Artifact | Path | Description |
|---|---|---|
| Spec | `outputs/documentation-and-onboarding/spec.md` | This file |
| Review | `outputs/documentation-and-onboarding/review.md` | Honest review of documentation quality and accuracy |

### Documentation Files

| File | Purpose |
|---|---|
| `README.md` | Gateway document: description, quickstart (5 commands), architecture diagram, directory structure, prerequisites, test command |
| `docs/contributor-guide.md` | Dev environment setup, project structure, coding conventions, making changes, plan-driven development |
| `docs/operator-quickstart.md` | Home hardware deployment: hardware reqs, installation, configuration, first boot, pairing, command center access, daily ops, recovery, security |
| `docs/api-reference.md` | Every daemon endpoint documented with method/path, auth, request/response JSON, error codes, curl examples |
| `docs/architecture.md` | System overview, module guide (each Python module), data flow, auth model, event spine, design decisions |

## Acceptance Criteria (from Plan)

- [x] README.md rewritten — under 200 lines, quickstart with 5 commands, architecture diagram, directory structure
- [x] `docs/contributor-guide.md` created — dev setup, running locally, project structure, making changes, coding conventions, plan-driven development
- [x] `docs/operator-quickstart.md` created — hardware requirements, installation, configuration, first boot, pairing, command center, daily ops, recovery, security
- [x] `docs/api-reference.md` created — all endpoints documented with curl examples
- [x] `docs/architecture.md` created — system overview, module guide, data flow, auth model, event spine, design decisions

## Design Decisions Captured

- Docs live in `docs/` — they travel with the code; no wiki drift
- README.md is a gateway, not a manual — under 200 lines; links to `docs/` for details
- All code in the stdlib — no external dependencies to document
- Architecture uses a LAN-only daemon binding by default (127.0.0.1 dev / LAN interface prod)
- Event spine is the source of truth; the inbox is a derived view

## Inputs Read

- `README.md` — existing high-level intro
- `SPEC.md` — spec writing guide
- `SPECS.md` — spec types reference
- `PLANS.md` — ExecPlan authoring guide
- `DESIGN.md` — visual and interaction design system
- `plans/2026-03-19-build-zend-home-command-center.md` — ExecPlan for milestone 1

## Code Files Read

- `services/home-miner-daemon/__init__.py`
- `services/home-miner-daemon/cli.py` — pairing, status, control, events commands
- `services/home-miner-daemon/daemon.py` — HTTP server, miner simulator, endpoints
- `services/home-miner-daemon/spine.py` — append-only event journal
- `services/home-miner-daemon/store.py` — principal/pairing persistence
- `apps/zend-home-gateway/index.html` — single-file command center UI
- `scripts/bootstrap_home_miner.sh` — daemon bootstrap with principal creation
- `scripts/pair_gateway_client.sh` — device pairing
- `scripts/read_miner_status.sh` — status read via CLI
- `scripts/set_mining_mode.sh` — control actions via CLI
- `scripts/hermes_summary_smoke.sh` — Hermes summary append
- `references/inbox-contract.md` — PrincipalId and pairing contracts
- `references/event-spine.md` — event spine schema and event kinds
- `upstream/manifest.lock.json` — pinned upstream dependencies

## Known Gaps (Not Fixed in This Lane)

- No CI job verifying quickstart commands against live daemon (deferred to lane 005)
- No curl examples in API reference that are scripted/verified automatically
- No test suite documentation beyond the `pytest` invocation (tests themselves not yet written per plan)
