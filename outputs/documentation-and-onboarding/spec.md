# Documentation & Onboarding — Specification

**Lane:** `documentation-and-onboarding`
**Status:** Milestone 1 Complete
**Generated:** 2026-03-22

---

## Overview

This document specifies the minimum required documentation surface for Zend
Home to be understood, deployed, and contributed to by operators and developers
who arrive with no prior context.

The documentation subsystem must achieve three goals:

1. **Operator onboarding** — a new home-user can set up Zend Home on a
   Raspberry Pi or mini PC, pair their phone, and operate the miner without
   reading source code.
2. **Contributor onboarding** — a new developer can clone the repo, run the
   daemon, and submit a working change without asking anyone for context.
3. **API accountability** — every daemon endpoint is documented with request
   shapes, response shapes, and named error codes that match `error-taxonomy.md`.

---

## Required Documents

### 1. README.md

**Purpose:** Land on a new reader. Answer "what is this?" and "how do I try it
right now?" in under five minutes.

**Required sections:**
- One-paragraph product description with the core invariant (phone = control
  plane, home miner = work plane)
- Quickstart (5 steps: bootstrap, pair, read status, control miner, audit)
- Architecture overview (ASCII system diagram or text diagram, key modules
  table)
- Current scope (what is and is not in milestone 1)
- Repository structure tree

**Quality bar:**
- A reader who has never seen the repo can run the 5-step quickstart from a
  single terminal and see working output.
- The architecture overview names all modules and explains how data flows from
  phone to miner and back.
- No unexplained jargon. Every term of art is defined on first use.

---

### 2. docs/contributor-guide.md

**Purpose:** Replace a 30-minute Slack conversation with a self-serve doc.

**Required sections:**
- Development environment setup (Python version, shell requirements, venv,
  install, verify)
- Running the daemon and gateway client locally
- Running smoke tests in sequence
- Repository conventions (spec vs plan, writing rules, code conventions, git
  conventions)
- How to add a new test
- Troubleshooting common failures (port in use, token expired, state
  corruption)
- Design system quick reference (fonts, colors, touch targets, banned patterns)

**Quality bar:**
- A developer who has never worked on this repo can `git clone`, run the daemon,
  and pass all smoke tests in under 20 minutes on a fresh machine.
- Every troubleshooting entry has a specific diagnosis and a specific recovery
  command, not just "check the logs."

---

### 3. docs/operator-quickstart.md

**Purpose:** Help a non-developer install and operate Zend Home on dedicated
home hardware (Raspberry Pi, mini PC, NAS).

**Required sections:**
- Hardware requirements table (recommended vs minimum)
- Step-by-step OS installation (Raspberry Pi OS Lite, SSH enable, hostname)
- Air-gap copy option for bandwidth-constrained environments
- Bootstrap and pairing walkthrough (daemon → pairing token → phone browser)
- Headless CLI pairing option
- Explanation of miner states and modes
- `systemd` service setup for auto-restart
- Upgrade procedure
- State reset procedure
- Network access guidance (do not port-forward; VPN for remote access)

**Quality bar:**
- An operator with basic Linux CLI experience can follow the guide from a
  flashed SD card to a working Zend Home installation without any other
  documentation.
- The network security note is unmissable — milestone 1 is LAN-only by design.

---

### 4. docs/api-reference.md

**Purpose:** Be the authoritative reference for every HTTP endpoint the daemon
exposes.

**Required sections:**
- Base URL and content type conventions
- One section per endpoint group: Health, Status, Miner Control, Pairing,
  Client Capabilities, Event Spine, Hermes Adapter
- Every endpoint must document: method, path, request headers, request body
  (if any), success response (200/201 with full JSON shape), error responses
  (all named error codes from `error-taxonomy.md` that the endpoint can return)
- Error reference table mapping error codes to HTTP status and description
- Note on authentication (X-Client-Name header + pairing store, no separate
  auth token)
- Note on rate limits and serialization policy
- API versioning approach

**Quality bar:**
- A developer implementing a client or debugging a failure can find every error
  code in this document, understand what caused it, and know exactly what the
  daemon returned.
- The error codes in this document match `references/error-taxonomy.md`
  exactly. No divergence.

---

### 5. docs/architecture.md

**Purpose:** Explain why the system is built the way it is, not just what the
files are.

**Required sections:**
- Design principles (5 invariants listed)
- Full system diagram (ASCII art or text representation with all components)
- Component descriptions: daemon, gateway client, event spine, inbox contract,
  pairing store, Hermes adapter — each with location, responsibilities,
  key data structures, and persistence model
- Pairing and authority state machine (text or ASCII diagram)
- Data flow diagram (input → validate → dispatch → append)
- Network topology diagram (LAN-only, future VPN/remot access placeholder)
- Principal identity explanation (why one UUID, shared across gateway and
  inbox)
- Observability section (log events table, metrics table)
- Recovery sequence
- Module map table (file → purpose)

**Quality bar:**
- A senior engineer reading only this document and `DESIGN.md` can draw the
  system from memory and locate every source file.
- The data flow diagram explains exactly where each error taxonomy code is
  generated.

---

## Quality Gates

All five documents must pass these gates before the lane is marked complete:

| Gate | Criterion |
|------|-----------|
| G1 | A reader with no prior context can run the README quickstart in ≤ 5 steps |
| G2 | A developer with no prior context can run the contributor guide in ≤ 20 minutes |
| G3 | An operator following the operator guide on a fresh Raspberry Pi gets a working Zend Home |
| G4 | Every error code in `error-taxonomy.md` appears in the API reference with a matching description |
| G5 | Every daemon endpoint appears in the API reference |
| G6 | Every module listed in the README architecture table has a corresponding entry in `docs/architecture.md` |
| G7 | The architecture document's system diagram is consistent with the README quickstart diagram |
| G8 | No broken links between documents (cross-references resolve) |
| G9 | No unexplained jargon — every term of art is defined on first use or linked to its definition |
| G10 | The word "simple" is not used to describe anything that is actually complex |

---

## Acceptance Criteria

- [ ] `README.md` rewritten with 5-step quickstart, architecture overview, and repo structure
- [ ] `docs/contributor-guide.md` created with dev setup, smoke tests, conventions, troubleshooting
- [ ] `docs/operator-quickstart.md` created with Raspberry Pi setup, systemd, pairing, recovery
- [ ] `docs/api-reference.md` created with all endpoints, all error codes, all request/response shapes
- [ ] `docs/architecture.md` created with full system diagram, component descriptions, state machines, data flow
- [ ] Gate G1–G10 all pass

---

## Dependencies

This lane depends on:

- `references/error-taxonomy.md` — must be accurate and complete before the API
  reference can be verified
- `references/event-spine.md` — must define all event kinds before the API
  reference's `/events` section can be written
- `DESIGN.md` — the contributor guide's design system section must match it
- `plans/2026-03-19-build-zend-home-command-center.md` — architecture doc must
  be consistent with the ExecPlan's diagrams
- `apps/zend-home-gateway/index.html` — must exist and be functional before the
  operator quickstart's browser-based pairing step can be tested

---

## Out of Scope

- Video tutorials or animated walkthroughs
- Internationalization (i18n) of documentation
- Search functionality for the docs
- Automated doc generation from code (e.g., OpenAPI tooling)
- Non-LAN deployment guide (deferred; see TODOS.md P1: Secure Remote Access)
