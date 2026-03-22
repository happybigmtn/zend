# Carried Forward: Build the Zend Home Command Center — Specification

**Status:** Carried Forward from Milestone 1
**Generated:** 2026-03-22
**Prior Lane:** `outputs/home-command-center/spec.md`

## Overview

This specification captures the remaining frontier tasks from the initial
Zend Home Command Center lane. The prior lane delivered repo scaffolding,
reference contracts, a Python daemon simulator, shell scripts, and a static
gateway client. This carried-forward lane addresses the gaps that prevent
the slice from meeting its own acceptance criteria.

## Frontier Tasks

These are the uncompleted items from the prior lane, each mapped to the
genesis plans that address them.

### 1. Automated Tests for Error Scenarios

**Genesis plan:** 004

The prior lane defined an error taxonomy in `references/error-taxonomy.md`
with ten named error classes but implemented zero automated tests. The
daemon, CLI, store, and spine modules have no test files. The following
error paths are untested:

- `PairingTokenExpired` and `PairingTokenReplay` (token validation is
  unimplemented, not merely untested)
- `GatewayUnauthorized` (capability check exists in CLI but not in daemon)
- `GatewayUnavailable` (daemon_call catches URLError but returns a dict,
  not a structured error)
- `MinerSnapshotStale` (no freshness threshold exists)
- `ControlCommandConflict` (no command serialization exists)
- `EventAppendFailed` (no error handling on file writes)
- `LocalHashingDetected` (audit script is a stub)

### 2. Tests for Trust Ceremony, Hermes Delegation, Event Spine Routing

**Genesis plans:** 004, 009, 012

No trust ceremony state machine exists in code. The pairing flow is
a direct `pair_client` call with no ceremony states (UNPAIRED →
PAIRED_OBSERVER → PAIRED_CONTROLLER). The Hermes adapter is a reference
contract only — no adapter code enforces delegation boundaries. Event
spine routing rules defined in `references/event-spine.md` are not
implemented; events are appended and read without routing.

### 3. Document Gateway Proof Transcripts

**Genesis plan:** 008

The plan requires `references/gateway-proof.md` with copiable proof
transcripts. This file does not exist. The bootstrap and pair scripts
emit JSON output that partially serves this purpose but is not collected
into a reproducible transcript document.

### 4. Implement Hermes Adapter

**Genesis plan:** 009

`references/hermes-adapter.md` defines the adapter interface but no
code implements it. `scripts/hermes_summary_smoke.sh` bypasses the
adapter entirely — it calls `spine.append_hermes_summary` directly
with no authority check, no capability validation, and no adapter
boundary.

### 5. Implement Encrypted Operations Inbox

**Genesis plans:** 011, 012

The event spine writes plaintext JSON to `state/event-spine.jsonl`.
No encryption exists. The spec and contracts require encrypted payloads,
but the implementation stores everything in cleartext. The inbox is
described as a "derived view" but no inbox projection exists — the
CLI `events` command reads the raw spine.

### 6. LAN-Only with Formal Verification

**Partially done.** The daemon binds `127.0.0.1` by default. However,
`ZEND_BIND_HOST` is configurable via environment variable with no
validation. Setting it to `0.0.0.0` silently exposes the daemon to the
network. No test verifies the binding constraint. No formal verification
exists.

## Architecture (Unchanged)

The architecture from the prior spec remains valid. See
`outputs/home-command-center/spec.md` for component locations, data
models, and interfaces. This carried-forward spec does not alter the
architecture; it addresses implementation gaps within it.

## Acceptance Criteria (Frontier)

- [ ] At least one automated test per error class in the taxonomy
- [ ] Trust ceremony state machine implemented and tested
- [ ] Hermes adapter code enforces capability boundaries
- [ ] Event spine payloads are encrypted at rest
- [ ] Inbox projection exists as a derived view of the spine
- [ ] Gateway proof transcripts documented in `references/gateway-proof.md`
- [ ] Bind-host validation rejects non-private addresses
- [ ] Token expiration and replay detection implemented and tested
- [ ] Control command serialization prevents concurrent conflicts

## Dependencies

Same as prior lane. No new external dependencies required for the
frontier tasks.
