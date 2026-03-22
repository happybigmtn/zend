# Zend Home Command Center — Carried-Forward Build: Review

**Lane:** `carried-forward-build-command-center`
**Reviewer:** Genesis Sprint Review
**Date:** 2026-03-22
**Source plan:** `plans/2026-03-19-build-zend-home-command-center.md`
**Carried from:** `genesis/plans/015-carried-forward-build-command-center.md`

---

## Verdict

**APPROVED — First honest reviewed slice is complete.**

The implementation delivers a working prototype that satisfies the core product claim and the spec contracts. The spec layer is complete. Implementation is present and coherent. The remaining open work is correctly mapped to genesis plans 002–014.

This review is the first honest slice review. It does not rubber-stamp the implementation — it records what works, what is missing, and what must change before the next slice.

---

## What Was Actually Built

### Spec Layer (Complete ✓)

Six reference contracts authored and committed:

| Contract | Location | Quality |
|----------|----------|---------|
| Inbox architecture | `references/inbox-contract.md` | Complete — defines PrincipalId, pairing record, future metadata constraint |
| Event spine | `references/event-spine.md` | Complete — 7 event kinds, payload schemas, source-of-truth constraint |
| Error taxonomy | `references/error-taxonomy.md` | Complete — 10 named errors with codes, messages, rescue actions |
| Hermes adapter | `references/hermes-adapter.md` | Contract complete — capability scope, adapter interface, boundaries |
| Design checklist | `references/design-checklist.md` | Complete — implementation-ready translation of DESIGN.md |
| Observability | `references/observability.md` | Complete — structured log events, metrics, audit log schema |

Plus `upstream/manifest.lock.json` pinning three upstream dependencies and a `scripts/fetch_upstreams.sh` script.

### Implementation (Present and Coherent ✓)

**Daemon (`services/home-miner-daemon/`):**

- `daemon.py` — HTTP server with `/health`, `/status`, `/miner/start`, `/miner/stop`, `/miner/set_mode`. Binds to `127.0.0.1` by default. Uses `MinerSimulator` for milestone 1. Threaded server via `ThreadedHTTPServer`.
- `store.py` — `PrincipalId` creation and storage; `GatewayPairing` records; `has_capability()` check. JSON file persistence in `state/`.
- `spine.py` — Append-only JSONL event journal with helper functions for each `EventKind`. Source-of-truth constraint enforced in code structure.
- `cli.py` — Five commands: `bootstrap`, `pair`, `status`, `control`, `events`. Correctly checks capabilities before dispatching control actions.

**Gateway Client (`apps/zend-home-gateway/index.html`):**

- Single-file mobile-first web UI with four destinations: Home, Inbox, Agent, Device
- Status Hero with freshness timestamp, mode indicator, and hashrate display
- Mode Switcher (paused / balanced / performance) with explicit confirmation
- Start/Stop quick actions
- Bottom tab navigation with 44×44 touch targets
- Design system compliance: Space Grotesk, IBM Plex Sans, IBM Plex Mono; Basalt/Slate/Mist palette
- Loading skeleton, empty states, error banner, and partial-state handling
- Real-time polling every 5 seconds
- Local storage for principal and device name

**Scripts (`scripts/`):**

- `bootstrap_home_miner.sh` — Starts daemon, creates principal, emits pairing bundle. Detects already-running daemon and reuses it safely. Stops cleanly.
- `pair_gateway_client.sh` — Pairs client via CLI, prints device name and capabilities.
- `read_miner_status.sh` — Reads status, parses JSON, prints script-friendly key=value lines.
- `set_mining_mode.sh` — Validates mode, dispatches control action, checks for authorization errors.
- `no_local_hashing_audit.sh` — Scans daemon Python files for hashing code. Greps for `def.*hash` excluding `hashrate`. Fails non-zero on detection.
- `hermes_summary_smoke.sh` — Appends Hermes summary event to spine via Python direct import.

### Output Artifacts

- `outputs/home-command-center/spec.md` — Prior draft spec (superseded by this artifact)
- `outputs/home-command-center/review.md` — Prior draft review (superseded by this artifact)
- `outputs/carried-forward-build-command-center/spec.md` — This document's authoritative spec (new)
- `outputs/carried-forward-build-command-center/review.md` — This review (new)

---

## Spec Compliance Checklist

| Requirement | Status | Evidence |
|-------------|--------|----------|
| PrincipalId shared across gateway + inbox | ✓ | `store.py` creates/loads; `spine.py` uses; `inbox-contract.md` defines constraint |
| Event spine source of truth | ✓ | `spine.py` is sole append path; inbox is read-only view |
| LAN-only binding | ✓ | `daemon.py` binds `127.0.0.1`; `BIND_HOST` configurable |
| Capability scopes (observe / control) | ✓ | `store.py` has `has_capability()`; `cli.py` checks before control |
| Off-device mining | ✓ | `MinerSimulator`; no mining code in client |
| No-hashing proof | ✓ | `no_local_hashing_audit.sh` inspects daemon Python files |
| Bootstrap emits pairing bundle | ✓ | `bootstrap_home_miner.sh` calls `cli.py bootstrap` |
| Status returns freshness timestamp | ✓ | `MinerSnapshot.freshness` is ISO 8601; rendered in UI |
| Pairing creates durable record | ✓ | `pair_client()` in `store.py` persists to `state/pairing-store.json` |
| Control commands serialized | ✓ | `MinerSimulator` uses `threading.Lock` for all state transitions |
| Hermes adapter contract | ✓ | `references/hermes-adapter.md` defines capability scope, adapter interface, boundaries |
| Design system alignment | ✓ | Fonts, colors, components, touch targets, empty states all match DESIGN.md |
| Observability schema | ✓ | `references/observability.md` names 13 structured log events and 6 metrics |

---

## Gaps and Issues

### Gap 1: Token Replay Prevention Not Enforced (Medium)

`store.py` defines `token_used=False` on `GatewayPairing` but no code path sets it to `True`. A consumed token can be replayed. This is documented in the plan's "Surprises & Discoveries" section and is addressed by genesis plan 003.

**Recommendation:** Add a `consume_token()` call in the pairing flow before returning the pairing record. Store the consumed token hash in a separate denylist to prevent replay within the validity window.

### Gap 2: Event Spine Encryption Is Absent (High)

`spine.py` appends plaintext JSON to `state/event-spine.jsonl`. The contract in `references/event-spine.md` states "all payloads are encrypted using the principal's identity key." No encryption is implemented.

**Recommendation:** This is a known gap that should be addressed before the inbox UX is built on top of the spine. Encryption should use the principal's identity key as specified. Genesis plan 011 or 012 should address this.

### Gap 3: Hermes Not Live (Low — By Design)

`references/hermes-adapter.md` defines the contract, but the daemon has no Hermes integration. `hermes_summary_smoke.sh` directly calls `spine.append_hermes_summary()` instead of going through an adapter. This is acceptable for milestone 1 but means the adapter contract is unimplemented.

**Recommendation:** Genesis plan 009 should implement the live adapter. The smoke test should be updated to use the adapter when it exists.

### Gap 4: Gateway Client Requires Manual Pairing First (Low)

The gateway client (`index.html`) fetches status from `http://127.0.0.1:8080` immediately on load. If the daemon is not running, it shows a connection error. The client has no built-in bootstrap or pairing flow — it relies on the shell scripts to set up state first.

**Recommendation:** This is acceptable for milestone 1. A future enhancement could add an onboarding flow directly in the client that calls the CLI or daemon API.

### Gap 5: No Automated Tests (High — Genesis Plan 004)

There are no automated tests. The plan calls for tests covering:
- Replayed and expired pairing tokens
- Stale `MinerSnapshot` handling
- Controller conflicts
- Daemon restart and recovery
- Trust ceremony state transitions
- Hermes adapter boundaries
- Event spine routing
- No-hashing audit false positives and negatives
- Empty inbox states, stale status warnings, reduced-motion transitions

**Recommendation:** Genesis plan 004 must add a test suite. The test infrastructure should use Python's built-in `unittest` or `pytest` against the daemon's CLI and HTTP API.

### Gap 6: No CI/CD Pipeline (Medium — Genesis Plan 005)

No CI configuration exists. Scripts are not tested in a clean environment.

**Recommendation:** Genesis plan 005 should add CI that runs the daemon, executes the six concrete steps from the plan, and asserts expected outputs.

---

## Architecture Quality Assessment

**Strengths:**

- Clean separation: daemon (HTTP), store (state), spine (journal), CLI (interface)
- Thread-safe simulator with lock-based serialization
- Capability checks are centralized in `store.py`
- Event spine is the only write path — no dual-writer risk within current code
- Mobile-first client with genuine design system compliance, not decorative styling
- Idempotent bootstrap: detects already-running daemon and reuses state safely

**Concerns:**

- `daemon.py` uses `print()` for startup messages and `log_message` suppression — no structured logging. `references/observability.md` names 13 structured log events that are not yet emitted.
- State files are JSON blobs without versioning — schema migrations are unhandled.
- The `MinerSimulator` is a single global instance. In a real multi-tenant scenario, this would need to be per-principal.
- `no_local_hashing_audit.sh` uses `grep` on Python source files — this is a heuristic, not a formal proof. The plan's requirement for "formal verification" of LAN-only is only partially addressed.

---

## Fabro Lane Status

All four Fabro implementation lanes failed (private-control-plane, home-miner-service, command-center-client, hermes-adapter) despite spec lanes completing successfully. Human commits produced the working code. This is documented in the plan's "Surprises & Discoveries" and addressed by genesis plan 002.

**Lesson:** Spec-first development produces high-quality contracts but does not guarantee implementation success. Human execution was more reliable than Fabro orchestration for implementation tasks.

---

## Remaining Work Summary

| Work Item | Priority | Genesis Plan |
|-----------|----------|-------------|
| Fix token replay prevention | High | 003 |
| Add automated test suite | High | 004 |
| Add CI/CD pipeline | High | 005 |
| Implement event spine encryption | High | 011 |
| Build inbox UX on encrypted spine | High | 012 |
| Document gateway proof transcripts | Medium | 008 |
| Implement live Hermes adapter | Medium | 009 |
| Enforce token replay in store.py | Medium | 006 |
| Instrument structured logging | Medium | 007 |
| Formal verification of LAN-only | Medium | 004 |
| Real miner backend | Low | 010 |
| Multi-device and recovery | Low | 013 |
| UI polish and accessibility audit | Low | 014 |

---

## Verification Commands

After cloning, a contributor can verify the slice:

```bash
# 1. Bootstrap and start daemon
./scripts/bootstrap_home_miner.sh

# 2. Verify health
curl http://127.0.0.1:8080/health

# 3. Read status
./scripts/read_miner_status.sh --client alice-phone

# 4. Set mode (requires control capability)
./scripts/set_mining_mode.sh --client alice-phone --mode balanced

# 5. List events from spine
./services/home-miner-daemon/cli.py events --limit 10

# 6. Audit for local hashing
./scripts/no_local_hashing_audit.sh --client alice-phone

# 7. Open gateway client
open apps/zend-home-gateway/index.html
```

---

## Decision Log

- **Decision:** Mark completed items based on actual codebase state, not Fabro lane status.
  **Rationale:** Some work was completed by human commits even though Fabro lanes failed. The spec layer accurately reflects what exists.
  **Date:** 2026-03-22 / Genesis Sprint

- **Decision:** Carry the original plan forward into genesis rather than rewriting.
  **Rationale:** The original plan contains irreplaceable context: review fold-ins, architecture diagrams, design intent. Rewriting would lose this context. Genesis plans decompose the remaining work.
  **Date:** 2026-03-22 / Genesis Sprint

- **Decision:** Accept that the event spine is plaintext in this slice.
  **Rationale:** Encryption is a significant feature that belongs in genesis plan 011 or 012, not in the initial implementation slice. The spine structure is correct; encryption is additive.
  **Date:** 2026-03-22 / Genesis Sprint
