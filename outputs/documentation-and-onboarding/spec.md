# Spec — Documentation & Onboarding

**Status:** Complete
**Lane:** `documentation-and-onboarding`
**Date:** 2026-03-23

## Purpose / User-Visible Outcome

After this work, a new contributor can go from cloning the repo to running the
full Zend system in under 10 minutes, following only the documentation. An
operator can deploy the daemon on home hardware using a quickstart guide. The
API is documented with working curl examples. The architecture is explained with
diagrams. No tribal knowledge is required.

## Scope

This spec covers all documentation deliverables for the Zend project:

- Rewrite `README.md` with quickstart, architecture diagram, directory
  structure, and links to deep-dive docs
- `docs/contributor-guide.md`: dev environment setup, project structure,
  making changes, coding conventions, plan-driven development, design system
- `docs/operator-quickstart.md`: hardware requirements, installation,
  configuration, first boot, daily operations, recovery, security
- `docs/api-reference.md`: every daemon endpoint with method, path,
  authentication, request/response shapes, curl examples, CLI reference
- `docs/architecture.md`: system overview, module guide, data flow,
  auth model, event spine, Hermes adapter, design decisions, adding a new
  endpoint

## Acceptance Criteria

| Criterion | Verification |
|---|---|
| README quickstart works from a fresh clone | Run bootstrap script, verify `status` returns valid JSON |
| Contributor guide covers all 8 sections | All section headings present in the file |
| Operator guide covers full lifecycle | All 9 sections present: hardware through security |
| API reference documents all 7 endpoints | Endpoint count matches `daemon.py` routes |
| Architecture doc module guide matches code | Every module in `services/home-miner-daemon/` has a section |
| All curl examples are syntactically valid | No missing headers, no malformed JSON |
| No references to files that don't exist | All linked docs exist at the linked paths |

## Decisions

- **Decision:** Documentation lives in `docs/` directory, not a wiki or external
  site. Rationale: docs should travel with the code. A wiki creates drift.
  Date/Author: 2026-03-22 / Genesis Sprint

- **Decision:** README.md is a gateway, not a manual. It is under 200 lines.
  Rationale: long READMEs get skimmed. The README tells you what Zend is, how
  to run it, and where to find more. Details live in `docs/`.
  Date/Author: 2026-03-22 / Genesis Sprint

- **Decision:** API reference uses `http://127.0.0.1:8080` as the base URL.
  Rationale: consistent with the default daemon binding for local development.
  Operators can substitute their LAN IP.
  Date/Author: 2026-03-23 / Documentation Sprint

- **Decision:** Architecture doc covers the full module guide by walking each
  file in `services/home-miner-daemon/`. Rationale: new engineers need a file-by-
  file orientation before they can navigate confidently.
  Date/Author: 2026-03-23 / Documentation Sprint

## What Was Produced

| File | Lines | Description |
|---|---|---|
| `README.md` | ~180 | Gateway doc: quickstart, ASCII diagram, dir structure, env vars, links |
| `docs/contributor-guide.md` | ~330 | Dev setup, local running, structure, making changes, conventions, plan-driven dev, design system, submitting |
| `docs/operator-quickstart.md` | ~300 | Hardware, install, env vars, first boot, pairing, daily ops, systemd, recovery, security |
| `docs/api-reference.md` | ~320 | 7 endpoints, request/response schemas, error responses, CLI commands, state files |
| `docs/architecture.md` | ~550 | System overview, ASCII diagram, module guide (4 modules), data flow, auth model, event spine, Hermes adapter, 6 design decisions, "adding a new endpoint" guide |

## Out of Scope

- CI verification of quickstart commands (deferred to plan 005)
- Scripted API reference validation (deferred to plan 005)
- Dark mode, internationalization, or localization of docs
- Versioned API docs or changelog
