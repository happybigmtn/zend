# Documentation & Onboarding — Specification

**Status:** Active
**Lane:** documentation-and-onboarding
**Generated:** 2026-03-23

## Purpose

This lane bootstraps the first honest reviewed slice of Zend documentation. The goal is a clean, repo-specific set of docs that let a contributor or operator land, understand the architecture, and act — without relying on external context, chat history, or institutional memory.

## Current Repo State

The repo is **docs-first at bootstrap**: scaffolding exists but no user-facing documentation has been written yet. Key facts about the current state:

| Area | Status |
|------|--------|
| `README.md` | Project overview exists; no quickstart, no architecture overview |
| `docs/` | Empty directory (only `.gitkeep`) |
| `services/home-miner-daemon/` | Contains daemon skeleton (Python, LAN-only) |
| `apps/zend-home-gateway/` | Contains mobile-first gateway client (HTML/JS) |
| `scripts/` | Bootstrap, pairing, status, control scripts |
| `references/` | inbox-contract.md and event-spine.md defined |
| `upstream/` | Manifest with pinned zcash dependencies |
| DESIGN.md | Full design system defined (typefaces, colors, motion) |
| SPEC.md / PLANS.md | Governing docs for spec and plan authoring |

The project does **not** yet have:
- A contributor guide
- An operator quickstart for home hardware
- An API reference
- An architecture document with system diagrams
- Any docs that have been verified on a clean machine

## Required Artifacts

### 1. `README.md` (rewrite)

Rewrite the top-level README to include:
- One-paragraph product description (what Zend is and why it matters)
- Quickstart (3–5 commands to go from clone to running)
- Architecture overview (2–3 sentences + ASCII diagram)
- Canonical document map (where to find what)
- Current scope statement (what exists vs. what is coming)

### 2. `docs/contributor-guide.md`

Dev-focused setup doc covering:
- Prerequisites (Python, Node, environment)
- Clone and bootstrap steps
- Running the home-miner daemon locally
- Running the gateway client locally
- Running scripts (bootstrap, pair, status, control)
- Running tests (if any)
- How to read the codebase (module map)
- How to contribute (branch model, PR process)
- Where specs and plans live and how to write them

### 3. `docs/operator-quickstart.md`

Home hardware deployment doc covering:
- What hardware is required (Raspberry Pi class or equivalent)
- How to flash and provision the base OS
- How to install and run the home-miner daemon
- How to pair a phone gateway over LAN
- How to operate the miner (start, stop, mode switch)
- How to read the inbox for operational receipts
- How to recover or factory-reset

### 4. `docs/api-reference.md`

Full endpoint and CLI reference covering:
- Daemon HTTP API (all endpoints: `/health`, `/status`, `/miner/start`, `/miner/stop`, `/miner/set_mode`)
- Request/response shapes for each endpoint
- Error codes and meanings
- CLI commands (bootstrap, pair, read-status, set-mode, hermes-summary-smoke, no-local-hashing-audit)
- Usage examples for every command
- PrincipalId and capability model

### 5. `docs/architecture.md`

System design doc covering:
- High-level architecture with ASCII diagram
- Component descriptions (daemon, gateway, event spine, inbox contract, Hermes adapter)
- Data flow for the core loop (command → daemon → event → inbox → gateway)
- Security model (LAN-only, capability scopes, off-device mining)
- Module map (what lives where, key files and their responsibilities)
- Design decisions recorded (why LAN-only, why event spine, why UUID PrincipalId)

## Acceptance Criteria

All criteria are **observable and testable**:

| # | Criterion | Test |
|---|-----------|------|
| 1 | README contains a quickstart that works on a clean machine | Clone + 5 commands → daemon running + gateway accessible |
| 2 | Contributor guide lists every prerequisite and setup step | New machine: follow guide → able to run all scripts |
| 3 | Operator quickstart works on Raspberry Pi class hardware | Flash OS + follow guide → miner controllable from phone |
| 4 | API reference covers every endpoint with correct shapes | Compare daemon source vs. doc → no missing fields |
| 5 | Architecture doc has a diagram matching actual component layout | Trace a command through the diagram → matches code |
| 6 | All four docs pass a lint/readability check | No dead links, no placeholder text, consistent style |
| 7 | Docs are verified on a clean machine | Followed README quickstart → succeeded without external help |

## Out of Scope

- User-facing marketing site
- Video tutorials
- Mobile app store listings
- Multi-node cluster deployment
- Wallet integration (Zcash or otherwise)
- Real mining hardware integration (daemon is a simulator for milestone 1)

## Dependencies

No new external dependencies. Documentation is written in Markdown using existing project conventions (see `SPEC.md` and `PLANS.md` for authoring rules).

## Risks

1. **Daemon not actually tested on clean machine** — Scripts may work in dev environment but fail elsewhere
2. **Architecture diagram drift** — As code evolves, docs can become stale; need a review gate
3. **Placeholder content** — Risk of writing docs that say "TBD" instead of real content
4. **Design system not applied** — Docs should respect DESIGN.md typography and color guidance

## Lane Completion Signal

This lane is complete when:
- All five artifacts exist at the specified paths
- Each artifact passes its acceptance criterion
- A clean-machine verification has been run and logged
