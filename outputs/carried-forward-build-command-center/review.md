# Zend Home Command Center — Slice 1 Review

**Reviewer:** Nemesis-style security + correctness
**Date:** 2026-03-22
**Verdict:** CONDITIONAL — architectural scaffold is sound; trust model does not
exist at runtime. Five graduation blockers must be fixed before this slice can
graduate from proof-of-shape to product foundation.

---

## Summary Assessment

**What the slice proves:** The correct *shape* of the command center — information
architecture, component vocabulary, data model, and script-driven operator flow.
All reference contracts are present and structurally aligned with the plan.

**What the slice does not prove:** The *trust model* the spec promises. Every
security property described in the spec (capability enforcement, token validation,
event encryption, staleness detection) exists only in documentation, not in running
code. The gap between spec-claim and daemon-reality is the primary blocker.

---

## Graduation Blockers

These five issues must be resolved before the slice can graduate:

### 1. Daemon has no authentication or capability enforcement [CRITICAL]

The daemon HTTP server (`services/home-miner-daemon/daemon.py`) accepts all requests
from any client on any endpoint (`/health`, `/status`, `/miner/start`, `/miner/stop`,
`/miner/set_mode`). No endpoint verifies client identity, checks capabilities, or
validates tokens.

The `observe`/`control` capability model exists only in the CLI layer (`cli.py`).
The gateway client (`apps/zend-home-gateway/index.html`) calls the daemon directly,
bypassing all CLI wrappers and all capability checks entirely.

**Consequence:** Any HTTP client can control the miner. The spec's claim that "a
paired observer cannot issue a control action" is false at the daemon boundary.

**Fix:** Move capability enforcement to the daemon HTTP boundary. Every mutation
endpoint must verify the client's capability scope before processing.

### 2. Pairing tokens are born expired and never validated [CRITICAL]

`store.py:89` sets `expires = datetime.now(timezone.utc).isoformat()` — the token
expires at the instant of creation. No code path checks expiration, validates a token,
or enforces `token_used`. The `--client` argument to scripts is a device name string,
not a secret.

**Consequence:** `PairingTokenExpired` and `PairingTokenReplay` from the error
taxonomy are defined but can never be raised. The trust ceremony described in the
plan does not exist at runtime.

**Fix:** Assign a real expiration window. Gate daemon operations with token validation.
Check and set `token_used` on every use.

### 3. Event spine writes plaintext [CRITICAL]

The spec describes an "append-only encrypted event journal" with payloads encrypted
using the principal's identity key. The implementation writes unencrypted JSON to
`event-spine.jsonl`.

**Consequence:** This is the largest gap between the spec's trust promise and the
runtime reality. Pairing events, control receipts, and Hermes summaries are readable
on disk in plaintext.

**Fix:** At minimum, add a symmetric encryption envelope using the principal's key
before writing to the spine.

### 4. Zero automated tests exist [HIGH]

The plan requires at least one automated test per script plus explicit tests for
error scenarios. No test files exist in the repository.

**Fix:** Add one smoke test per script. Add explicit tests for: replayed/expired
pairing tokens, stale snapshots, control command conflicts, daemon restart recovery,
trust-ceremony state transitions, Hermes adapter boundaries, event spine routing,
and observe-only denial copy.

### 5. Gateway proof transcripts are missing [HIGH]

`references/gateway-proof.md` is required by the plan but does not exist. The plan
lists `references/onboarding-storyboard.md` as a required artifact; it also does not
exist.

**Fix:** Add both files with copiable transcripts and narrative onboarding walkthrough.

---

## Should-Fix Before Next Milestone

| # | Issue | Location | Impact |
|---|-------|---------|--------|
| 6 | Hermes adapter is a contract only | `references/hermes-adapter.md` | "Hermes connects only through adapter" is not enforceable |
| 7 | Control command serialization absent | `daemon.py` | Concurrent POSTs both succeed; `ControlCommandConflict` never raised |
| 8 | Staleness detection absent | `daemon.py`, `index.html` | `.stale` CSS class defined but never applied; `MinerSnapshotStale` never raised |
| 9 | No CORS headers on daemon | `daemon.py` | LAN browser access from non-`127.0.0.1` origin is blocked |
| 10 | BIND_HOST has no guardrail | `daemon.py` | Setting `ZEND_BIND_HOST=0.0.0.0` exposes unauthenticated daemon |
| 11 | Shell injection in hermes_summary_smoke.sh | line 52 | Bash vars interpolated into Python string literal |
| 12 | Design system colors wrong | `index.html` | Warm stone palette instead of Basalt/Slate/Mist/Moss/Amber/Signal Red/Ice |
| 13 | Accessibility not implemented | `index.html` | No ARIA landmarks, live regions, keyboard nav, or reduced-motion |
| 14 | Upstream SHAs not pinned | `upstream/manifest.lock.json` | All `pinned_sha: null`, tracking `main` |
| 15 | Bootstrap skips `pairing_requested` event | `cli.py:cmd_bootstrap()` | Spine audit trail inconsistent with `cmd_pair()` |
| 16 | Store and spine not transactional | `cli.py:cmd_pair()` | Partial failure leaves inconsistent state |
| 17 | Control receipt appended non-atomically | `cli.py:cmd_control()` | Action recorded in daemon before receipt; no rollback if receipt write fails |
| 18 | Spine events have no deduplication | `services/spine.py` | Retried appends create duplicate events |

---

## What the Slice Does Well

- **PrincipalId** is correctly shared across store, spine, and pairing records
- **Event spine as source of truth** — inbox is correctly a derived view, not a
  parallel write path
- **Script-driven operator flow** matches the plan's "scripts first, agent-callable
  later" philosophy
- **Information architecture** (Home, Inbox, Agent, Device) and **component
  vocabulary** (Status Hero, Mode Switcher, Receipt Card, Permission Pill) match
  `DESIGN.md` exactly
- **Daemon binds localhost** by default — correct LAN-only starting position
- **Miner simulator** exposes the same contract a real backend would use

---

## Repo Path Notes

The lane expects artifacts at `outputs/carried-forward-build-command-center/`. The
specify stage originally wrote to `outputs/home-command-center/`. This review places
artifacts in the correct lane path.

---

## Verdict

**CONDITIONAL.** The scaffold is structurally complete and architecturally sound. Fix
the five graduation blockers — daemon auth, token lifecycle, spine encryption,
automated tests, and proof transcripts — to advance this slice from proof-of-shape
to product foundation.
