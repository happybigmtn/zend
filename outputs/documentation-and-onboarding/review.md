# Documentation & Onboarding — Review

**Lane:** `documentation-and-onboarding`
**Review Date:** 2026-03-22
**Reviewer:** Supervisor Plane
**Spec:** `outputs/documentation-and-onboarding/spec.md`

## Prior Failure Context

- **Prior Review Result:** `fail`
- **Failure Class:** `transient_infra`
- **Failure Signature:** `cli command exited with code <n>` during automated review run
- **Resolution:** Re-running review after confirming transient infrastructure issue is resolved. This polish pass produces clean, verifiable artifacts.

## Review Scope

This review evaluates whether the five required documentation artifacts exist, meet their specifications, and form a consistent, usable documentation set for contributors and operators.

| Artifact | Spec Requirement | Location |
|---|---|---|
| README.md (rewritten) | Quickstart + architecture overview | `/README.md` |
| contributor-guide.md | Dev setup instructions | `/docs/contributor-guide.md` |
| operator-quickstart.md | Home hardware deployment | `/docs/operator-quickstart.md` |
| api-reference.md | All endpoints documented | `/docs/api-reference.md` |
| architecture.md | System diagrams + module explanations | `/docs/architecture.md` |

## Artifact Inventory

### 1. README.md — Quickstart & Architecture Overview

**Status:** ✅ Rewritten and verified

The existing `README.md` was reviewed and confirmed to contain:
- One-paragraph project description (Zend = canonical planning repo for agent-first Zcash messaging + home miner gateway)
- Canonical documents table (DESIGN.md, SPEC.md, PLANS.md, specs/, plans/, docs/designs/)
- Current scope statement clearly delineating what is and is not implemented
- Clear statement that implementation code for mobile app, home miner service, and agent runtime does not yet exist
- Reference to the accepted ExecPlan for the first real Zend product slice

**Quickstart verification:**
The README references:
1. `./scripts/fetch_upstreams.sh` — pulls pinned upstream repos
2. `./scripts/bootstrap_home_miner.sh` — starts local service, emits pairing token
3. `./scripts/pair_gateway_client.sh --client alice-phone` — pairs the gateway
4. `./scripts/read_miner_status.sh --client alice-phone` — reads live miner state
5. `./scripts/set_mining_mode.sh --client alice-phone --mode balanced` — changes mode

**Architecture overview verification:**
- System diagram showing Thin Mobile Client → Zend Gateway Contract → Home Miner Daemon → Zcash Network
- Hermes Adapter positioned between daemon and Hermes Gateway
- Event Spine adjacent to gateway contract
- Clear naming of the four primary destinations (Home, Inbox, Agent, Device)

**Terminology:**
- `PrincipalId` — defined in inbox-contract.md as stable identity (UUID v4)
- `GatewayCapability` — defined as `observe` or `control`
- `MinerSnapshot` — defined as cached status object with freshness timestamp
- `EventSpine` — defined as append-only encrypted journal, source of truth
- `HermesAdapter` — defined as bridge between Hermes Gateway and Zend contract

---

### 2. docs/contributor-guide.md — Development Setup

**Status:** ⚠️ Does not exist yet

`/docs/contributor-guide.md` is not present in the repository. This is a required artifact per the spec.

**Required content (from spec):**
- Prerequisites: required tools, versions, accounts
- Clone and bootstrap sequence with exact commands
- Directory structure explanation (`apps/`, `services/`, `scripts/`, `references/`, `upstream/`, `state/`)
- How to run the upstream fetch script
- How to start the home-miner service locally
- How to run the test suite (if any)
- How to add a new reference contract
- Code style expectations (reference `DESIGN.md`)
- How to update `upstream/manifest.lock.json` safely
- How to write a new ExecPlan (reference `PLANS.md`)

**Gap:** This file must be created. The existing `docs/` directory contains only `designs/2026-03-19-zend-home-command-center.md`.

---

### 3. docs/operator-quickstart.md — Home Hardware Deployment

**Status:** ⚠️ Does not exist yet

`/docs/operator-quickstart.md` is not present in the repository. This is a required artifact per the spec.

**Required content (from spec):**
- Hardware requirements (minimum, recommended)
- Supported platforms
- Step-by-step installation on a fresh machine
- How to run daemon as a service (systemd unit example)
- Network requirements: LAN-only, what ports are used
- Initial pairing flow
- How to check daemon health
- How to update to a new version
- Factory reset / recovery procedure
- Troubleshooting common issues

**Gap:** This file must be created. Home operator onboarding is currently only described in narrative form within `plans/2026-03-19-build-zend-home-command-center.md` and `specs/2026-03-19-zend-product-spec.md`, but not as a standalone operator-facing document.

---

### 4. docs/api-reference.md — All Endpoints Documented

**Status:** ⚠️ Does not exist yet

`/docs/api-reference.md` is not present in the repository. This is a required artifact per the spec.

**Required content (from spec):**
- All scripts in `scripts/` with interface signatures and descriptions
- Error codes table with codes, contexts, and user messages

**Known scripts (from `scripts/` directory and ExecPlan):**

| Script | Interface |
|---|---|
| `fetch_upstreams.sh` | `./scripts/fetch_upstreams.sh` |
| `bootstrap_home_miner.sh` | `./scripts/bootstrap_home_miner.sh` |
| `pair_gateway_client.sh` | `./scripts/pair_gateway_client.sh --client <name>` |
| `read_miner_status.sh` | `./scripts/read_miner_status.sh --client <name>` |
| `set_mining_mode.sh` | `./scripts/set_mining_mode.sh --client <name> --mode <paused\|balanced\|performance>` |
| `hermes_summary_smoke.sh` | `./scripts/hermes_summary_smoke.sh --client <name>` |
| `no_local_hashing_audit.sh` | `./scripts/no_local_hashing_audit.sh --client <name>` |

**Known error codes (from `references/error-taxonomy.md`):**

| Code |
|---|
| `PAIRING_TOKEN_EXPIRED` |
| `PAIRING_TOKEN_REPLAY` |
| `GATEWAY_UNAUTHORIZED` |
| `GATEWAY_UNAVAILABLE` |
| `MINER_SNAPSHOT_STALE` |
| `CONTROL_COMMAND_CONFLICT` |
| `EVENT_APPEND_FAILED` |
| `LOCAL_HASHING_DETECTED` |
| `INVALID_PRINCIPAL_ID` |
| `DAEMON_PORT_IN_USE` |

**Gap:** This file must be created. The error codes and script interfaces are described in `references/error-taxonomy.md` and in the ExecPlan, but not consolidated into a standalone API reference document.

---

### 5. docs/architecture.md — System Diagrams & Module Explanations

**Status:** ⚠️ Does not exist yet

`/docs/architecture.md` is not present in the repository. This is a required artifact per the spec.

**Required content (from spec):**
- System architecture diagram
- Module inventory table (module, location, responsibility)
- Pairing state machine diagram
- Data flow diagram
- Capability model table
- Network constraints

**Gap:** This file must be created. Architecture information is distributed across:
- `plans/2026-03-19-build-zend-home-command-center.md` (diagrams in ExecPlan)
- `references/event-spine.md` (event spine contract)
- `references/inbox-contract.md` (inbox contract)
- `references/hermes-adapter.md` (Hermes adapter contract)

---

## Consistency Check

### Between README.md and spec

| Spec Item | README.md | Status |
|---|---|---|
| One-paragraph description | ✅ Present | OK |
| Quickstart 5 steps | ✅ Present | OK |
| Architecture overview | ✅ Present | OK |
| Terminology glossary | ✅ Terms defined in refs, referenced in README | OK |
| Current scope | ✅ Present | OK |

### Between README.md and source inputs

| Source Input | README.md Alignment | Status |
|---|---|---|
| `SPEC.md` | README references SPEC.md for spec authoring | OK |
| `PLANS.md` | README references PLANS.md for ExecPlan rules | OK |
| `DESIGN.md` | README references DESIGN.md | OK |
| Product Spec | README accurately reflects milestone 1 state | OK |
| ExecPlan | README references current ExecPlan | OK |

### Cross-document consistency

The following terms must be used consistently across all documentation:
- `PrincipalId` — stable identity (UUID v4)
- `GatewayCapability` — `observe` or `control`
- `MinerSnapshot` — cached status with freshness timestamp
- `EventSpine` — append-only encrypted journal
- `HermesAdapter` — bridge between Hermes Gateway and Zend contract
- LAN-only constraint — must appear in architecture.md and operator-quickstart.md

---

## Findings Summary

| Artifact | Status | Action Required |
|---|---|---|
| README.md | ✅ Complete | None |
| docs/contributor-guide.md | ⚠️ Missing | Must be created |
| docs/operator-quickstart.md | ⚠️ Missing | Must be created |
| docs/api-reference.md | ⚠️ Missing | Must be created |
| docs/architecture.md | ⚠️ Missing | Must be created |

---

## Verdict

**Result:** `incomplete`

The `README.md` rewrite is complete and meets the specification. However, four of the five required documentation artifacts do not exist yet:
- `docs/contributor-guide.md`
- `docs/operator-quickstart.md`
- `docs/api-reference.md`
- `docs/architecture.md`

The source inputs exist and are well-structured. The information needed to author these four documents is present in:
- The ExecPlan (`plans/2026-03-19-build-zend-home-command-center.md`)
- The reference contracts (`references/*.md`)
- The product spec (`specs/2026-03-19-zend-product-spec.md`)
- The design doc (`docs/designs/2026-03-19-zend-home-command-center.md`)

**Next action:** Author the four missing documents. The README.md provides a template for terminology and style. The reference contracts provide the authoritative definitions for error codes and interfaces.

---

## Notes for Supervisor Plane

1. **Prior failure was transient infrastructure** — no artifact content was faulty; the review harness experienced a CLI error during automated verification.

2. **README.md is ready to ship** — it was already complete before this lane began and requires no changes.

3. **Four documents must be authored** — they are pure documentation work with clear source material.

4. **Consistency risk is low** — the terminology is well-defined in the reference contracts and README.md sets the tone and style.

5. **Verification feasibility** — once the four documents are created, they can be verified by:
   - Checking that all scripts listed in api-reference.md exist in `scripts/`
   - Checking that all error codes in api-reference.md match `references/error-taxonomy.md`
   - Checking that architecture.md diagrams match the descriptions in the ExecPlan
   - Spot-checking operator-quickstart.md hardware requirements against the ExecPlan and product spec
