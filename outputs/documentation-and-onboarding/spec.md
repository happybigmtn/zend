# SPEC: Documentation & Onboarding

## Status

Accepted — 2026-03-22

## Purpose / User-Visible Outcome

After this work, a new contributor can go from cloning the repo to running the
full Zend system in under 10 minutes, following only the documentation. An
operator can deploy the daemon on home hardware using only the operator quickstart
guide. The API is documented with working curl examples. The architecture is
explained with diagrams. No tribal knowledge is required.

## Scope

This spec covers all user-facing documentation for the Zend milestone 1 product:

- **README.md** — rewritten as a gateway, not a manual. Under 200 lines.
  Includes one-paragraph description, quickstart (5 commands), architecture
  diagram (ASCII), directory structure, links to deep-dive docs, prerequisites,
  and test command.

- **docs/contributor-guide.md** — dev environment setup, running locally,
  project structure rationale, making changes, coding conventions, plan-driven
  development guide, design system pointer, and submitting changes checklist.

- **docs/operator-quickstart.md** — hardware requirements, installation
  (clone, no pip install), environment variable configuration, first boot
  walkthrough with expected output, device pairing, command center access,
  daily operations (status, mode, start/stop), recovery procedures,
  headless deployment (systemd unit), and security notes.

- **docs/api-reference.md** — every daemon endpoint documented with method,
  path, authentication requirement, request body, response format, error
  codes, and curl example. Covers all existing endpoints and the planned
  `GET /spine/events` and `POST /pairing/refresh` from plan 006.

- **docs/architecture.md** — system overview diagram, module guide for each
  Python module (daemon.py, store.py, spine.py, cli.py, index.html), data
  flow for control commands and pairing, auth model, design decision
  rationale, and instructions for adding a new endpoint.

## Acceptance Criteria

1. README quickstart: a reader can follow the six commands from a fresh clone
   and see the daemon health check return `{"healthy": true}`.

2. Contributor guide: a developer who has never seen the repo can set up their
   environment and run the test suite by following only this document.

3. Operator quickstart: an operator following the guide on a Raspberry Pi can
   start the daemon, pair a phone, and see miner status in the browser.

4. API reference: every curl example in the document works against a running
   daemon and produces the documented output.

5. Architecture doc: an engineer can read this document and accurately predict
   how a new endpoint would be implemented, where it would go, and what
   patterns it would follow.

## What Is Not Covered

- Automated test suite (0 tests exist; not part of this lane)
- Milestone 2+ features (Hermes integration beyond stubs, encrypted memo inbox,
  remote access, payout-target mutation)
- Build or deployment tooling beyond shell scripts
- Mobile app development
- Performance benchmarking or load testing

## Verification Method

Verified by following each document from a clean environment (fresh clone, no
pre-existing `state/` directory) and confirming the expected outputs match
actual outputs. All curl examples tested against the live daemon. Results are
recorded in `outputs/documentation-and-onboarding/review.md`.

## Relationship to ExecPlan

This spec is the contract. The ExecPlan at
`genesis/plans/008-documentation-and-onboarding.md` captures the living
implementation progress, decision log, and discoveries.

## Code Fixes Included in This Lane

During documentation verification, two bugs were found and fixed:

1. **Enum serialization** (`daemon.py`): `MinerSimulator` returned raw enum objects
   (e.g. `MinerStatus.STOPPED`) instead of string values (`"stopped"`) in
   `start()`, `stop()`, `set_mode()`, and `get_snapshot()` responses. Fixed by
   using `.value` on all enum returns.

2. **Missing `/spine/events` endpoint** (`daemon.py`): The daemon returned
   `404 not_found` for `GET /spine/events` despite the endpoint being documented.
   Fixed by adding the route to `GatewayHandler.do_GET()`.

