# Spec: Documentation & Onboarding

Status: Accepted

This spec defines the documentation deliverables for the Zend project: the
rewritten README, the contributor guide, the operator quickstart, the API
reference, and the architecture document.

## Purpose / User-Visible Outcome

After this work, a new contributor can go from a fresh clone to a running,
tested Zend Home system in under 10 minutes, following only the in-repo
documentation. An operator can deploy the daemon on a Raspberry Pi or similar
Linux box using the operator quickstart. The API is documented with working
curl examples. The architecture is explained with diagrams and module guides.
No tribal knowledge is required.

## Whole-System Goal

Zend must be understandable and operable without access to chat history,
external wikis, or the original engineers. All knowledge needed to use and
contribute to the project must travel with the code.

## Scope

### Deliverables

1. **README.md** (rewrite) — one-paragraph description, 5-command quickstart,
   architecture diagram, directory structure, environment variables, key concepts,
   links to deep-dive docs. Under 200 lines.

2. **docs/contributor-guide.md** — dev environment setup, running locally,
   project structure explanation, making changes workflow, coding conventions,
   plan-driven development guide, design system pointer, submitting changes,
   recovery procedures.

3. **docs/operator-quickstart.md** — hardware requirements, installation,
   configuration (environment variables), first boot walkthrough, pairing a phone,
   opening the command center, daily operations, recovery procedures,
   systemd service setup, security notes.

4. **docs/api-reference.md** — every daemon HTTP endpoint documented with method,
   path, authentication requirement, request body, response format with example
   JSON, error responses, and a curl example. Coverage of the event spine via CLI.

5. **docs/architecture.md** — system overview diagram, module-by-module guide
   (purpose, key classes/functions, state managed), data flow diagrams,
   auth model explanation, design decisions with rationale.

### Non-Deliverables

- Code changes (no implementation work in this lane)
- Tests for documentation accuracy (deferred to lane verification step)
- CI automation (deferred to a later lane)
- External site or wiki hosting

## Current State

The current README.md is a high-level introduction that does not include
practical run instructions. The project has no contributor guide, no operator
guide, no API reference, and no architecture document. A newcomer must read
multiple files (the plan, the spec, the design doc, the daemon source) to
understand how to bootstrap and operate the system.

## Architecture / Runtime Contract

The documentation must accurately reflect the current implementation:

- Daemon: `services/home-miner-daemon/daemon.py`, `ThreadedHTTPServer`, LAN-only,
  stdlib only, binds to `ZEND_BIND_HOST:ZEND_BIND_PORT`
- CLI: `services/home-miner-daemon/cli.py`, subcommands: health, status,
  bootstrap, pair, control, events
- Spine: `services/home-miner-daemon/spine.py`, append-only JSONL at
  `state/event-spine.jsonl`
- Store: `services/home-miner-daemon/store.py`, principal + pairing at
  `state/principal.json` and `state/pairing-store.json`
- UI: `apps/zend-home-gateway/index.html`, single HTML file, polls
  `http://<host>:<port>/status` every 5 seconds
- Bootstrap: `scripts/bootstrap_home_miner.sh`
- Pairing: `scripts/pair_gateway_client.sh`

## Acceptance Criteria

All of the following must be true:

- README.md quickstart works from a fresh clone and produces documented output
- Contributor guide enables test suite execution without external help
- Operator quickstart covers full deployment lifecycle on a Raspberry Pi or
  similar Linux box
- API reference curl examples all work against a running daemon and produce
  documented output
- Architecture document correctly describes every module and data flow
- No document contains broken links to other in-repo files
- All environment variables documented are correct
- All endpoint paths and response shapes match `daemon.py`

## Decision Log

- Decision: Documentation lives in `docs/` and the repo root, not a wiki or
  external site.
  Rationale: Docs should travel with the code. A wiki creates drift.
  Date/Author: 2026-03-22 / Genesis Sprint

- Decision: README.md is a gateway, not a manual. It must stay under 200 lines.
  Rationale: Long READMEs get skimmed. The README tells you what Zend is, how
  to run it, and where to find more.
  Date/Author: 2026-03-22 / Genesis Sprint

- Decision: The daemon's HTTP endpoints are documented as-is, not as they
  should be.
  Rationale: Documentation must reflect the current system. Future auth or
  capability enforcement changes go into the docs when they land in code.
  Date/Author: 2026-03-22 / Genesis Sprint

- Decision: API reference documents the daemon's HTTP endpoints and the CLI's
  event spine interface separately.
  Rationale: The event spine is not a direct HTTP endpoint — it is CLI-only.
  Documenting it as a separate interface avoids implying network accessibility
  that does not exist.
  Date/Author: 2026-03-22 / Genesis Sprint

## Failure Handling

- **Documentation drifts from code:** Mitigation: every PR that changes daemon
  endpoints must update `docs/api-reference.md`. Enforced by review, not CI
  (CI for documentation is deferred).
- **Quickstart commands stop working:** Mitigation: the review artifact includes
  a verification pass on a clean machine.
- **Architecture document describes a module that does not exist:** Mitigation:
  the document is generated from reading the actual source files, not imagined
  from the spec.
