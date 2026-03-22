# Carried Forward: Build the Zend Home Command Center — Review

**Status:** Milestone 1 — NOT APPROVED
**Reviewed:** 2026-03-22
**Reviewer:** Nemesis-style security review (two-pass)

## Verdict

**REJECTED.** The scaffolding and documentation layers are strong, but the
enforcement layer is hollow. The existing `outputs/home-command-center/review.md`
approves the slice prematurely — it marks the slice complete while the ExecPlan's
own Progress section still shows most implementation items unchecked. Six of the
plan's thirteen acceptance criteria are not actually enforced in code. Zero
automated tests exist. The most critical finding is that the capability system
exists only in the CLI wrapper, not in the daemon — any process on localhost can
control the miner by hitting the HTTP endpoints directly, bypassing all
authorization.

## Artifact Path Mismatch

The specify stage wrote artifacts to `outputs/home-command-center/` but the
lane expects them at `outputs/carried-forward-build-command-center/`. This
review corrects the path. The spec has been copied to the required location.

## What's Genuinely Good

- **Directory structure** matches the ExecPlan precisely.
- **Reference documents** (error taxonomy, hermes adapter contract, inbox
  contract, event spine contract, observability spec) are well-written and
  internally consistent.
- **Design system compliance** in the HTML client is strong — correct
  typography (Space Grotesk, IBM Plex Sans, IBM Plex Mono), correct color
  tokens, correct component vocabulary (Status Hero, Mode Switcher, Receipt
  Card, Permission Pill), mobile-first layout with bottom tab bar.
- **PrincipalId threading** is consistent across store, spine, and CLI.
- **Event spine as JSONL** with typed event kinds is a reasonable M1 approach.
- **CLI architecture** is clean — single entry point with subcommands, thin
  shell script wrappers.
- **MinerSimulator** correctly uses threading locks for in-memory state.

---

## Nemesis Pass 1 — First-Principles Trust Boundary Challenges

### CRITICAL: Daemon has zero authentication

`daemon.py` exposes `/miner/start`, `/miner/stop`, `/miner/set_mode` with no
authentication. The capability system (`observe` vs `control`) is enforced only
in `cli.py`, not in the HTTP layer. Any process on the host can `curl
http://127.0.0.1:8080/miner/stop` and halt mining without any capability check.

The entire authorization model is cosmetic — it exists in a wrapper layer that
can be trivially bypassed.

**Location:** `services/home-miner-daemon/daemon.py:168-200`
**Impact:** Complete bypass of capability scoping.
**Required fix:** The daemon must validate a bearer token or client identity
on every mutating endpoint. Capability checks must live in the daemon, not
only in the CLI.

### CRITICAL: No trust ceremony exists

The spec and plan both call for a "trust ceremony" during pairing. The
implementation is `pair_client()` in `store.py:93-119`, which creates a JSON
record. There is no challenge-response, no out-of-band verification, no user
confirmation, and no cryptographic binding between a client and its principal.

**Location:** `services/home-miner-daemon/store.py:93-119`
**Impact:** "Trust ceremony" is a documentation fiction. Any process that can
call the CLI can pair itself.

### HIGH: Pairing tokens are never validated

`create_pairing_token()` at `store.py:86-89` sets `token_expires_at` to
`datetime.now()` — the token is expired at creation time. But expiration is
never checked anywhere. The `token_used` field on `GatewayPairing` is never
set to `True` after use. The error taxonomy defines `PairingTokenExpired` and
`PairingTokenReplay` but neither error is ever raised.

**Location:** `services/home-miner-daemon/store.py:86-89`
**Impact:** The token lifecycle is a no-op. Replay attacks are undetectable.

### HIGH: ZEND_BIND_HOST allows network exposure

The daemon defaults to `127.0.0.1` but accepts `ZEND_BIND_HOST` from the
environment without validation. Setting `ZEND_BIND_HOST=0.0.0.0` exposes the
unauthenticated, unauthorized daemon to the entire network. Combined with the
zero-authentication finding above, this turns a LAN machine into an open
miner control surface.

**Location:** `services/home-miner-daemon/daemon.py:34`
**Impact:** Milestone 1's LAN-only guarantee is not enforced, only defaulted.
**Required fix:** Validate that bind address is a loopback or link-local
address, or require an explicit opt-in flag for non-loopback binding.

### MEDIUM: PrincipalId has no cryptographic binding

A PrincipalId is a UUID stored in `state/principal.json` as plaintext. There
is no signature, no key derivation, no proof of possession. Any process that
can read the state directory can impersonate the principal.

**Location:** `services/home-miner-daemon/store.py:52-69`

### MEDIUM: State directory path traversal

`ZEND_STATE_DIR` is taken from the environment without sanitization. A
malicious environment variable could redirect state writes to arbitrary
filesystem locations.

**Location:** `services/home-miner-daemon/daemon.py:30`, `store.py:25`,
`spine.py:22`

---

## Nemesis Pass 2 — Coupled State and Protocol Surfaces

### CRITICAL: Store and spine are decoupled write paths

The spec says "the event spine is the source of truth and the inbox is a
derived view." But the store and spine are written independently:

1. `cmd_pair()` at `cli.py:98-128` writes to the store first (`pair_client()`),
   then appends events to the spine. If the process crashes after the store
   write but before spine append, the pairing exists but the event trail is
   incomplete.
2. Capability checks in `has_capability()` read from the **store**, not the
   spine. The spine is not the source of truth for authorization — the store is.

This means the spec's core invariant ("spine is source of truth") is violated
in practice. The store is the real authority, and the spine is a best-effort
audit log.

**Impact:** If the store and spine diverge, the system has no reconciliation
path. A pairing could exist in the store with no corresponding spine event,
or vice versa.

### HIGH: Bootstrap vs pair event asymmetry

`cmd_bootstrap()` at `cli.py:73-95` appends only `pairing_granted` to the
spine. `cmd_pair()` at `cli.py:98-128` appends both `pairing_requested` then
`pairing_granted`. The spine has different event sequences for the same logical
operation depending on the entry point. Any future inbox projection that
expects `requested` before `granted` will break for bootstrap-created pairings.

**Location:** `cli.py:89-93` vs `cli.py:106-115`

### HIGH: No encryption on the "encrypted" event spine

The docstring at `spine.py:1-6` says "append-only encrypted event journal."
The spec says "encrypted event spine." Events are appended as plaintext JSON
to a JSONL file. There is no encryption at all. The "encrypted" qualifier is
a documentation lie.

**Location:** `services/home-miner-daemon/spine.py:62-65`
**Impact:** Any process that can read `state/event-spine.jsonl` sees all
events in plaintext — pairing records, control receipts, Hermes summaries.

### HIGH: Uptime counter grows while miner is stopped

`MinerSimulator.start()` sets `_started_at` but `stop()` never clears it.
`get_snapshot()` computes `_uptime_seconds = int(time.time() - _started_at)`
whenever `_started_at` is truthy. After stopping the miner, `_started_at`
still holds the old value, so uptime appears to keep growing even while
stopped. The snapshot reports incorrect data.

**Location:** `services/home-miner-daemon/daemon.py:106-113` (stop) and
`daemon.py:135-148` (get_snapshot)

### HIGH: Control serialization not implemented

The plan says "control commands must be serialized" and the error taxonomy
defines `ControlCommandConflict`. The daemon has no serialization. The
threading lock in `MinerSimulator` prevents concurrent in-memory mutations
but not command-level serialization. Two concurrent HTTP `POST /miner/start`
requests can both be processed. No `ControlCommandConflict` error is ever
raised.

**Location:** `services/home-miner-daemon/daemon.py:186-200`

### MEDIUM: JSONL corruption on partial write

If `_save_event()` at `spine.py:62-65` crashes mid-write (e.g., disk full,
process kill), the JSONL file will have a truncated last line.
`_load_events()` calls `json.loads(line)` on each line — a truncated line
will raise `JSONDecodeError`, making the entire spine unreadable. There is no
recovery path for a corrupted spine.

**Location:** `services/home-miner-daemon/spine.py:50-59`

### MEDIUM: File-level race conditions in store

`store.py` does read-modify-write on `pairing-store.json` without file
locking. Two concurrent `pair_client()` calls could both read the same
state, each write their new pairing, and the second write would silently
overwrite the first.

**Location:** `services/home-miner-daemon/store.py:72-83`

### MEDIUM: Gateway client hardcodes capabilities and principal

`index.html:626` hardcodes `capabilities: ['observe', 'control']`. The UI
always shows control buttons regardless of actual paired capabilities. There
is no capability negotiation with the daemon.

`index.html:781` falls back to a well-known example UUID
(`550e8400-e29b-41d4-a716-446655440000`) for the principal ID.

**Location:** `apps/zend-home-gateway/index.html:626-628` and `781`

### MEDIUM: No event deduplication

Calling the same script twice appends duplicate events with different UUIDs.
There is no idempotency key. Combined with the error taxonomy's suggestion to
"retry append" on `EventAppendFailed`, retry-without-dedup means double writes.

### LOW: Stale snapshot detection is a no-op

The daemon always returns `datetime.now(timezone.utc).isoformat()` as
freshness. There is no actual freshness threshold. The `MinerSnapshotStale`
error is defined in the taxonomy but never raised. The client-side freshness
display will never show stale data because the daemon always reports "now."

**Location:** `services/home-miner-daemon/daemon.py:147`

### LOW: No CORS headers

The daemon sets no CORS headers. The gateway client in `index.html` makes
`fetch()` calls to `http://127.0.0.1:8080`. If the HTML is served from any
origin other than `127.0.0.1:8080`, browsers will block the requests.

---

## Acceptance Criteria Gap Analysis

| Criterion (from ExecPlan) | Status | Evidence |
|---|---|---|
| Daemon starts locally on LAN-only | Partial | Default is localhost but `ZEND_BIND_HOST` allows bypass |
| Pairing creates PrincipalId and capability record | Partial | Record created, but token lifecycle is a no-op |
| Status endpoint returns MinerSnapshot with freshness | Bug | Freshness always "now"; uptime grows while stopped |
| Control requires 'control' capability | Broken | Only enforced in CLI, not daemon HTTP |
| Events append to encrypted spine | Broken | Not encrypted, truncation-fragile |
| Inbox shows receipts, alerts, summaries | Partial | Empty placeholders in UI, no data flow |
| Gateway client proves no local hashing | Stub | `no_local_hashing_audit.sh` is a stub |
| Trust ceremony | Missing | No ceremony exists |
| Serialized control commands | Missing | No serialization, no conflict detection |
| Automated tests | Missing | Zero test files |
| Gateway proof transcripts | Missing | `references/gateway-proof.md` does not exist |
| Onboarding storyboard | Missing | `references/onboarding-storyboard.md` does not exist |
| Hermes connects only through adapter | Contract only | No live integration, smoke script appends directly |

## Remaining Blockers (Ordered by Severity)

1. **Daemon authentication** — must enforce capabilities at the HTTP layer
2. **Store/spine consistency** — must resolve which is actually source of truth
3. **Encryption** — must encrypt spine events or stop calling it encrypted
4. **Token lifecycle** — must implement expiration and replay detection
5. **Trust ceremony** — must implement actual pairing verification
6. **Control serialization** — must detect and reject conflicting commands
7. **Uptime bug** — must clear `_started_at` on stop
8. **Bind address validation** — must reject `0.0.0.0` in milestone 1
9. **Automated tests** — zero exist, plan requires extensive coverage
10. **Gateway proof transcripts** — required artifact does not exist
11. **JSONL corruption recovery** — spine must tolerate partial writes
12. **Gateway client capability negotiation** — must read actual capabilities

## Milestone Fit

The scaffolding, contracts, and documentation are milestone-appropriate. The
implementation is not. The delta between "spec says" and "code enforces" is
too large to approve. The existing review at `outputs/home-command-center/review.md`
should be superseded by this review.

The spec file at `outputs/carried-forward-build-command-center/spec.md` is
accurate as a description of intent. It should not be changed — the
implementation must be brought up to meet it.
