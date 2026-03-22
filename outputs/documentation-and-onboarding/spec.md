# Documentation & Onboarding — Specification

**Status:** Ready for Implementation
**Lane:** `documentation-and-onboarding`
**Generated:** 2026-03-22

## Purpose

Bootstrap the first honest reviewed documentation slice for Zend, a private command center that combines encrypted Zcash-based messaging with a mobile gateway into a home miner. This artifact defines what documentation must exist, where it lives, and what it must cover.

## What This Produces

After this lane completes, a new contributor or home operator can:

1. Clone the repository and understand Zend's architecture in minutes
2. Set up a local development environment without asking questions
3. Deploy the home-miner control service on real hardware
4. Understand every API endpoint and script available
5. Follow the documentation step-by-step on a clean machine and succeed

## Source Inputs

| Input | Location | Purpose |
|---|---|---|
| README.md | `/README.md` | Project overview, current scope |
| SPEC.md | `/SPEC.md` | Guide for durable specs |
| SPECS.md | `/SPECS.md` | ExecPlan requirements |
| PLANS.md | `/PLANS.md` | Executable plan rules |
| DESIGN.md | `/DESIGN.md` | Visual and interaction design system |
| Product Spec | `/specs/2026-03-19-zend-product-spec.md` | Accepted capability spec |
| ExecPlan | `/plans/2026-03-19-build-zend-home-command-center.md` | First implementation slice |
| Design Doc | `/docs/designs/2026-03-19-zend-home-command-center.md` | CEO-mode product direction |
| Reference Contracts | `/references/*.md` | Inbox, event-spine, error, Hermes contracts |

## Required Documentation Artifacts

### 1. `README.md` — Quickstart & Architecture Overview

**Location:** `/README.md`
**Owner:** This lane rewrites the existing README.

**What it must contain:**

- One-paragraph description: what Zend is and why it matters
- The canonical documents table (updated to reflect current state)
- Quickstart: 5 steps from clone to running daemon
- Architecture overview diagram showing the four system layers:
  - Thin Mobile Client → Zend Gateway Contract → Home Miner Daemon → Zcash Network
  - Including Hermes Adapter and Event Spine positions
- Key terminology glossary (3–5 terms: `PrincipalId`, `GatewayCapability`, `MinerSnapshot`, `EventSpine`, `HermesAdapter`)
- Current scope statement (what IS and IS NOT in this repo)
- CI/environment requirements

**What it must NOT contain:**
- Marketing language or slogans
- Generic "built with X" badges unless they affect development
- Links to external docs that are not mirrored in this repo

---

### 2. `docs/contributor-guide.md` — Development Setup

**Location:** `/docs/contributor-guide.md`
**New file.**

**What it must contain:**

- Prerequisites: required tools, versions, accounts
- Clone and bootstrap sequence with exact commands
- Directory structure explanation (what lives in `apps/`, `services/`, `scripts/`, `references/`, `upstream/`, `state/`)
- How to run the upstream fetch script
- How to start the home-miner service locally
- How to run the test suite (if any)
- How to add a new reference contract
- Code style expectations (reference `DESIGN.md` for frontend)
- How to update `upstream/manifest.lock.json` safely
- How to write a new ExecPlan (reference `PLANS.md`)

**What it must NOT contain:**
- Assumptions about IDE or OS beyond "Unix-like environment"
- Instructions that require external SaaS accounts for local dev

---

### 3. `docs/operator-quickstart.md` — Home Hardware Deployment

**Location:** `/docs/operator-quickstart.md`
**New file.**

**What it must contain:**

- Hardware requirements (minimum, recommended)
- Supported platforms
- Step-by-step installation on a fresh machine
- How to run the daemon as a service (systemd unit example)
- Network requirements: LAN-only by default, what ports are used
- Initial pairing flow (phone/app to home miner)
- How to check daemon health
- How to update to a new version
- Factory reset / recovery procedure
- Troubleshooting common issues

**What it must NOT contain:**
- Remote access instructions (out of scope for milestone 1)
- Payout configuration (deferred)

---

### 4. `docs/api-reference.md` — All Endpoints Documented

**Location:** `/docs/api-reference.md`
**New file.**

**What it must cover:**

#### Daemon Control API (scripts in `scripts/`)

| Script | Interface | What it does |
|---|---|---|
| `fetch_upstreams.sh` | ` ./scripts/fetch_upstreams.sh` | Fetch pinned upstream repos into `third_party/` |
| `bootstrap_home_miner.sh` | `./scripts/bootstrap_home_miner.sh` | Start daemon, create `PrincipalId`, emit pairing token |
| `pair_gateway_client.sh` | `./scripts/pair_gateway_client.sh --client <name>` | Pair a named client with `observe` capability |
| `read_miner_status.sh` | `./scripts/read_miner_status.sh --client <name>` | Print miner status, mode, freshness timestamp |
| `set_mining_mode.sh` | `./scripts/set_mining_mode.sh --client <name> --mode <paused\|balanced\|performance>` | Change miner mode, append receipt |
| `hermes_summary_smoke.sh` | `./scripts/hermes_summary_smoke.sh --client <name>` | Connect Hermes, append summary to event spine |
| `no_local_hashing_audit.sh` | `./scripts/no_local_hashing_audit.sh --client <name>` | Audit gateway client, fail if hashing detected |

#### Error Codes

| Code | Context | User Message |
|---|---|---|
| `PAIRING_TOKEN_EXPIRED` | Token past validity window | "This pairing request has expired." |
| `PAIRING_TOKEN_REPLAY` | Token already consumed | "This pairing request has already been used." |
| `GATEWAY_UNAUTHORIZED` | Missing capability | "You don't have permission." |
| `GATEWAY_UNAVAILABLE` | Daemon unreachable | "Unable to connect to Zend Home." |
| `MINER_SNAPSHOT_STALE` | Snapshot past freshness threshold | "Showing cached status." |
| `CONTROL_COMMAND_CONFLICT` | In-flight command collision | "Another control action is in progress." |
| `EVENT_APPEND_FAILED` | Spine write failed | "Unable to save this operation." |
| `LOCAL_HASHING_DETECTED` | Hashing work on client | "Security warning: unexpected mining activity." |

---

### 5. `docs/architecture.md` — System Diagrams & Module Explanations

**Location:** `/docs/architecture.md`
**New file.**

**What it must contain:**

#### System Architecture Diagram

```
Thin Mobile Client
       |
       | pair + observe + control + inbox
       v
Zend Gateway Contract
    |           |
    |           +--> Zend Event Spine
    v
Home Miner Daemon
    |        |
    |        +--> Hermes Adapter --> Hermes Gateway
    |
    +--> Miner backend or simulator
              |
              v
         Zcash network
```

#### Module Inventory

| Module | Location | Responsibility |
|---|---|---|
| Gateway Contract | `services/` | Secure pairing, capability enforcement, control serialization |
| Event Spine | `services/` | Append-only encrypted journal, source of truth |
| Hermes Adapter | `services/hermes-adapter/` | Translate Hermes authority to Zend capabilities |
| Home Miner Daemon | `services/home-miner/` | Miner control, status snapshots, LAN-only binding |
| Command Center Client | `apps/` | Thin mobile-shaped UI, pairing, status, inbox view |
| Scripts | `scripts/` | Operator CLI for bootstrap, pairing, control, audit |
| References | `references/` | Durable contracts: inbox, event-spine, errors, Hermes |

#### Pairing State Machine

```
UNPAIRED --> PAIRED_OBSERVER --> PAIRED_CONTROLLER
                |                       |
                | revoke/expire        | revoke/expire
                v                       v
           CONTROL_ACTION --> REJECTED
                |
                v
         RECEIPT APPENDED TO EVENT SPINE
```

#### Data Flow

```
INPUT --> VALIDATE --> TRANSFORM --> APPEND
  |          |            |           |
 nil token  invalid cap  daemon off   append fail
 empty name expired token stale snap  inbox decrypt
 no agent   unauthorized control conflict Hermes reject
```

#### Capability Model

| Scope | Can Do |
|---|---|
| `observe` | Read miner status, read inbox |
| `control` | Change mining mode (paused/balanced/performance) |

#### Network Constraints

- Milestone 1: LAN-only binding
- Daemon binds to private interface only (never `0.0.0.0` in milestone 1)
- No internet-facing control surface
- Remote access deferred

---

## Verification Requirement

All documentation must be verifiable by following it on a clean machine. For this lane, "clean" means:

1. A new Unix-like environment with no pre-installed Zend dependencies
2. Following the `README.md` quickstart produces a running daemon
3. Following the `contributor-guide.md` setup produces a working dev environment
4. Following the `operator-quickstart.md` produces a correctly deployed home miner

Documentation that cannot be followed end-to-end on a clean machine must be flagged as incomplete.

## Durability

These documents are durable. They describe stable behavior and canonical locations. They must be updated when:
- A new service module is added to `services/`
- A new script is added to `scripts/`
- The architecture changes materially
- A new capability or error class is introduced

They must NOT be updated for:
- Transient experimental code
-临时 debug flags
- One-off scripts that don't affect operators

## Relationship to Other Documents

| Document | Relationship |
|---|---|
| `README.md` | Entry point; leads to `docs/architecture.md` and `docs/contributor-guide.md` |
| `docs/contributor-guide.md` | Leads to `PLANS.md` for ExecPlan authoring |
| `docs/operator-quickstart.md` | Leads to `docs/api-reference.md` for script details |
| `docs/architecture.md` | Detailed reference; supports both contributor and operator paths |
| `docs/api-reference.md` | Reference; linked from `README.md` and `operator-quickstart.md` |

## What Is NOT in This Lane

- Implementation of any feature
- Tests (those belong in the feature implementation lane)
- Visual design assets beyond what is in `DESIGN.md`
- Marketing copy or landing pages
- Remote access documentation
- Payout configuration

---

## Acceptance Criteria

1. `README.md` is rewritten with quickstart (5 steps) and architecture overview
2. `docs/contributor-guide.md` exists with complete dev setup
3. `docs/operator-quickstart.md` exists with home hardware deployment instructions
4. `docs/api-reference.md` documents all scripts and error codes
5. `docs/architecture.md` contains system diagrams and module explanations
6. All five documents are consistent with each other and with the source inputs
7. A human can follow the `README.md` quickstart on a clean machine and succeed
