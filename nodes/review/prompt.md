Goal: Documentation & Onboarding

Bootstrap the first honest reviewed slice for this frontier.

Inputs:
- `README.md`
- `SPEC.md`
- `SPECS.md`
- `PLANS.md`
- `DESIGN.md`
- `genesis/plans/001-master-plan.md`

Current frontier tasks:
- Rewrite README.md with quickstart and architecture overview
- Create docs/contributor-guide.md with dev setup instructions
- Create docs/operator-quickstart.md for home hardware deployment
- Create docs/api-reference.md with all endpoints documented
- Create docs/architecture.md with system diagrams and module explanations
- Verify documentation accuracy by following it on a clean machine

Required durable artifacts:
- `outputs/documentation-and-onboarding/spec.md`
- `outputs/documentation-and-onboarding/review.md`


## Completed stages
- **specify**: success
  - Model: MiniMax-M2.7-highspeed, 73.3k tokens in / 415 out
  - Files: README.md, docs/api-reference.md, docs/architecture.md, docs/contributor-guide.md, docs/operator-quickstart.md, outputs/documentation-and-onboarding/review.md, outputs/documentation-and-onboarding/spec.md, services/home-miner-daemon/daemon.py


# Documentation & Onboarding Lane — Review

Review the lane outcome for `documentation-and-onboarding`.

Focus on:
- correctness
- milestone fit
- remaining blockers

If a small direct source fix is needed to make the review judgment truthful and unblock the lane, you may make it, but stay inside the touched surfaces.


Lane context:
Plan file:
- `genesis/plans/008-documentation-and-onboarding.md`

Full plan context (read this for domain knowledge, design decisions, and specifications):

# Documentation & Onboarding

This ExecPlan is a living document. The sections `Progress`, `Surprises & Discoveries`, `Decision Log`, and `Outcomes & Retrospective` must be kept up to date as work proceeds. Maintained in accordance with `genesis/PLANS.md`.

## Purpose / Big Picture

After this work, a new contributor can go from cloning the repo to running the full Zend system in under 10 minutes, following only the documentation. An operator can deploy the daemon on home hardware using a quickstart guide. The API is documented with request/response examples. The architecture is explained with diagrams. No tribal knowledge is required.

## Progress

- [ ] Rewrite README.md with quickstart and architecture overview
- [ ] Create docs/contributor-guide.md with dev setup instructions
- [ ] Create docs/operator-quickstart.md for home hardware deployment
- [ ] Create docs/api-reference.md with all endpoints documented
- [ ] Create docs/architecture.md with system diagrams and module explanations
- [ ] Verify documentation accuracy by following it on a clean machine

## Surprises & Discoveries

(To be updated during implementation.)

## Decision Log

- Decision: Documentation lives in `docs/` directory, not wiki or external site.
  Rationale: Docs should travel with the code. A wiki creates drift. Everything should be verifiable from a clone.
  Date/Author: 2026-03-22 / Genesis Sprint

- Decision: README.md is a gateway, not a manual. It should be under 200 lines.
  Rationale: Long READMEs get skimmed. The README should tell you what Zend is, how to run it, and where to find more. Details go in `docs/`.
  Date/Author: 2026-03-22 / Genesis Sprint

## Outcomes & Retrospective

(To be updated at completion.)

## Context and Orientation

The current README.md at the repo root is a high-level introduction but doesn't include practical instructions for running the system. A newcomer would need to read multiple files (SPEC.md, the plan, reference contracts) to understand how to bootstrap the daemon and pair a device.

The system is simple: start a Python daemon, run a bootstrap script, open an HTML file. But the steps aren't documented in one place.

Key files this plan creates or modifies:
- `README.md` (rewrite)
- `docs/contributor-guide.md` (new)
- `docs/operator-quickstart.md` (new)
- `docs/api-reference.md` (new)
- `docs/architecture.md` (new)

## Plan of Work

### Milestone 1: README Rewrite (days 1–3)

Rewrite `README.md` to include:

1. **One-paragraph description** — what Zend is, who it's for
2. **Quickstart** — 5 commands to go from clone to working system:

        git clone <repo-url> && cd zend
        ./scripts/bootstrap_home_miner.sh
        # Open apps/zend-home-gateway/index.html in browser
        python3 services/home-miner-daemon/cli.py status --client my-phone
        python3 services/home-miner-daemon/cli.py control --client my-phone --action set_mode --mode balanced

3. **Architecture diagram** — ASCII, same as `genesis/SPEC.md`
4. **Directory structure** — what's in each top-level directory
5. **Links** — to docs/, specs/, plans/, references/ for deep dives
6. **Prerequisites** — Python 3.10+, no other dependencies
7. **Running tests** — `python3 -m pytest services/home-miner-daemon/ -v`

Keep it under 200 lines. No marketing language. No roadmap (that's in plans/).

Proof: A reader can follow the README quickstart from a fresh clone and see the daemon health check return `{"status": "ok"}`.

### Milestone 2: Contributor Guide (days 3–5)

Create `docs/contributor-guide.md` covering:

1. **Dev environment setup** — Python version, virtual environment, installing pytest
2. **Running locally** — bootstrap, daemon, client, all scripts explained
3. **Project structure** — what each directory contains and why
4. **Making changes** — how to edit code, run tests, verify
5. **Coding conventions** — Python style (stdlib only, no external deps), naming, error handling
6. **Plan-driven development** — how ExecPlans work, how to update them
7. **Design system** — pointer to DESIGN.md, how to verify UI changes
8. **Submitting changes** — branch naming, PR template, CI checks

Proof: A contributor who has never seen the repo can set up their environment and run the test suite by following only this document.

### Milestone 3: Operator Quickstart (days 5–6)

Create `docs/operator-quickstart.md` for someone deploying Zend on home hardware:

1. **Hardware requirements** — any Linux box with Python 3.10+
2. **Installation** — clone repo, no pip install needed
3. **Configuration** — environment variables (ZEND_BIND_HOST, ZEND_BIND_PORT, ZEND_STATE_DIR, ZEND_TOKEN_TTL_HOURS)
4. **First boot** — bootstrap script walkthrough with expected output
5. **Pairing a phone** — step-by-step with expected output
6. **Opening the command center** — how to access index.html from the phone's browser
7. **Daily operations** — checking status, changing mode, viewing events
8. **Recovery** — what to do when state is corrupted, when daemon won't start
9. **Security** — LAN-only binding, what to check, what not to expose

Proof: Follow the guide on a Raspberry Pi or similar Linux box. Daemon starts, phone pairs, status renders in browser.

### Milestone 4: API Reference (days 6–7)

Create `docs/api-reference.md` documenting every daemon endpoint:

For each endpoint:
- Method and path
- Authentication requirement (none, observe, control)
- Request body (if applicable)
- Response format with example JSON
- Error responses with codes
- curl example

Endpoints to document:
- `GET /health`
- `GET /status`
- `GET /spine/events`
- `GET /metrics`
- `POST /miner/start`
- `POST /miner/stop`
- `POST /miner/set_mode`
- `POST /pairing/refresh` (from plan 006)

Proof: Every curl example in the document works against a running daemon and produces the documented output.

### Milestone 5: Architecture Document (days 7–8)

Create `docs/architecture.md` with:

1. **System overview** — ASCII diagram of all components and their relationships
2. **Module guide** — for each Python module: purpose, key functions, state it manages
3. **Data flow** — how a control command flows from client → daemon → spine → response
4. **Auth model** — how pairing, capabilities, and tokens work together
5. **Event spine** — how events are appended, queried, and routed to the inbox
6. **Design decisions** — why stdlib-only, why LAN-only, why JSONL not SQLite, why single HTML file

Proof: A new engineer can read this document and accurately predict how a new endpoint would be implemented, where it would go, and what patterns it would follow.

## Validation and Acceptance

1. Fresh clone → working system in under 10 minutes following README only
2. Contributor guide enables test suite execution without tribal knowledge
3. Operator guide covers full deployment lifecycle on home hardware
4. API reference curl examples all work against running daemon
5. Architecture doc correctly describes the current system (verified by reading code)

## Failure Scenarios

- **Documentation drifts from code:** The quickstart commands stop working after code changes. Mitigation: CI job that runs the quickstart commands and verifies expected output (add after plan 005).
- **API reference has wrong response format:** Endpoint responses change but docs aren't updated. Mitigation: API reference includes curl commands that can be scripted and verified.
- **Operator guide assumes network topology:** Home networks vary wildly. Mitigation: Document the minimum requirement (Python 3, LAN access) and troubleshoot common failures (firewall, port forwarding).

## Idempotence and Recovery

Documentation is additive. All changes are Markdown files that can be overwritten safely.

## Interfaces and Dependencies

New files:
- `docs/contributor-guide.md`
- `docs/operator-quickstart.md`
- `docs/api-reference.md`
- `docs/architecture.md`

Modified files:
- `README.md` (rewrite)

No code changes. No new dependencies.


Active plan:
- `genesis/plans/001-master-plan.md`

Active spec:
- `genesis/SPEC.md`

Mapping notes:
- composite plan mapped from plan structure; humans may refine the checked-in contract later

Open tasks:
- Rewrite README.md with quickstart and architecture overview
- Create docs/contributor-guide.md with dev setup instructions
- Create docs/operator-quickstart.md for home hardware deployment
- Create docs/api-reference.md with all endpoints documented
- Create docs/architecture.md with system diagrams and module explanations
- Verify documentation accuracy by following it on a clean machine

Artifacts to write:
- `spec.md`
- `review.md`


Nemesis-style security review
- Pass 1 — first-principles challenge: question trust boundaries, authority assumptions, and who can trigger the slice's dangerous actions
- Pass 2 — coupled-state review: identify paired state or protocol surfaces and check that every mutation path keeps them consistent or explains the asymmetry
- check state transitions that affect balances, commitments, randomness, payout safety, or replayability
- check secret handling, capability scoping, pairing/idempotence behavior, and privilege escalation paths
- check external-process control, operator safety, idempotent retries, and failure modes around service lifecycle