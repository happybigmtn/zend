# Zend Home Command Center — Milestone 1 Review

**Lane:** carried-forward-build-command-center
**Status:** Milestone 1 — NOT APPROVED
**Reviewed:** 2026-03-22
**Reviewer:** Nemesis-style security review (two-pass)
**Supervisory context:** This review supersedes the prior approval at
`outputs/home-command-center/review.md`, which was issued prematurely. The
implementation delta from spec intent is too large for approval.

---

## Verdict

**REJECTED.**

The scaffolding, reference contracts, and documentation are milestone-appropriate.
The enforcement layer is hollow. Six of the ExecPlan's thirteen acceptance
criteria are not enforced in code. Zero automated tests exist. The most critical
finding: the capability system exists only in the CLI wrapper — the daemon HTTP
endpoints accept every mutating request unconditionally. Any process on localhost
can halt mining without any authorization check.

---

## What's Genuinely Good

- **Directory structure** matches the ExecPlan precisely.
- **Reference documents** — inbox contract, event spine, error taxonomy, Hermes
  adapter, observability spec — are well-written and internally consistent.
- **Design system compliance** in the HTML client is strong: correct typography
  (Space Grotesk, IBM Plex Sans, IBM Plex Mono), correct color tokens, correct
  component vocabulary (Status Hero, Mode Switcher, Receipt Card, Permission
  Pill), mobile-first layout with bottom tab bar.
- **PrincipalId threading** is consistent across store, spine, and CLI.
- **Event spine as JSONL** with typed event kinds is a reasonable M1 approach.
- **CLI architecture** is clean — single entry point with subcommands, thin shell
  wrappers.
- **MinerSimulator** uses threading locks for in-memory state.

---

## Pass 1 — First-Principles Trust Boundary Challenges

### CRITICAL: Daemon has zero HTTP-layer authentication

`daemon.py:168-200` exposes `/miner/start`, `/miner/stop`, `/miner/set_mode` with
no token validation, no capability check, and no identity verification. The
capability system (`observe` vs `control`) is enforced only in `cli.py`, not in
the HTTP server. Any process on the host can `curl http://127.0.0.1:8080/miner/stop`
and halt mining immediately.

The entire authorization model is cosmetic — it exists in a wrapper layer that
can be trivially bypassed by calling the HTTP API directly.

**Location:** `services/home-miner-daemon/daemon.py:168-200`
**Impact:** Complete bypass of capability scoping.
**Required fix:** The daemon must validate a bearer token or client identity on
every mutating endpoint. Capability checks must live in the daemon, not only in
the CLI wrapper.

### CRITICAL: No trust ceremony exists

The spec and ExecPlan both call for a "trust ceremony" during pairing. The
implementation is `store.py:pair_client()` — a function that writes a JSON record.
There is no challenge-response, no out-of-band verification, no user
confirmation, and no cryptographic binding between a client and its principal.

**Location:** `services/home-miner-daemon/store.py:93-119`
**Impact:** "Trust ceremony" is a documentation fiction. Any process that can
invoke the CLI can pair itself as a controller.

### HIGH: Pairing tokens are never validated

`store.py:create_pairing_token()` sets `token_expires_at = datetime.now()` — the
token is expired at creation time. But expiration is never checked anywhere. The
`token_used` field on `GatewayPairing` is never set to `True` after use. The
error taxonomy defines `PairingTokenExpired` and `PairingTokenReplay` but neither
error is ever raised.

**Location:** `services/home-miner-daemon/store.py:86-89`
**Impact:** Token lifecycle is a no-op. Replay attacks are undetectable.

### HIGH: Bind address is not enforced to LAN-only

The daemon defaults to `127.0.0.1` but accepts `ZEND_BIND_HOST` from the
environment without validation. Setting `ZEND_BIND_HOST=0.0.0.0` exposes the
unauthenticated daemon to the entire network. Combined with the missing
authentication finding, this turns a home machine into an open miner control
surface with no authorization whatsoever.

**Location:** `services/home-miner-daemon/daemon.py:34`
**Impact:** Milestone 1's LAN-only guarantee is not enforced, only defaulted.
**Required fix:** Validate that the bind address is a loopback or link-local
address, or require an explicit opt-in flag for non-loopback binding.

### MEDIUM: PrincipalId has no cryptographic binding

A PrincipalId is a UUID stored in `state/principal.json` as plaintext. There is
no signature, no key derivation, no proof of possession. Any process that can
read the state directory can claim any principal identity.

**Location:** `services/home-miner-daemon/store.py:52-69`

### MEDIUM: State directory path traversal risk

`ZEND_STATE_DIR` is taken from the environment without sanitization. A
malicious or misconfigured environment variable could redirect state writes to
arbitrary filesystem locations.

**Location:** `services/home-miner-daemon/daemon.py:30`, `store.py:25`,
`spine.py:22`

---

## Pass 2 — Coupled State and Protocol Surfaces

### CRITICAL: Store and spine are independent write paths

The spec says "the event spine is the source of truth and the inbox is a derived
view." In practice, `cli.py:cmd_pair()` writes to the store first, then appends
to the spine. If the process crashes between the two writes, the pairing exists
but the event trail is incomplete. More critically, `has_capability()` reads
from the **store**, not the spine — the spine is not the source of truth for
authorization.

The spec's core invariant is violated: the store is the real authority, and the
spine is a best-effort audit log with no enforcement role.

**Impact:** If the store and spine diverge, the system has no reconciliation
path.

### HIGH: Bootstrap vs pair event asymmetry

`cli.py:cmd_bootstrap()` appends only `pairing_granted` to the spine.
`cli.py:cmd_pair()` appends both `pairing_requested` then `pairing_granted`. The
same logical operation produces different event sequences depending on entry
point. Any future inbox projection that expects `requested` before `granted` will
break for bootstrap-created pairings.

**Location:** `services/home-miner-daemon/cli.py:89-93` vs `cli.py:106-115`

### HIGH: Event spine is not encrypted

The docstring at `spine.py:1-6` describes an "append-only encrypted event
journal." The spec says "encrypted event spine." Events are appended as
plaintext JSON to a JSONL file. There is no encryption at rest. Any process
that can read `state/event-spine.jsonl` sees all events in plaintext — pairing
records, control receipts, Hermes summaries.

**Location:** `services/home-miner-daemon/spine.py:62-65`
**Impact:** The "encrypted" qualifier is a documentation misstatement.

### HIGH: Uptime grows while miner is stopped

`MinerSimulator.start()` sets `_started_at`. `stop()` never clears it.
`get_snapshot()` computes `_uptime_seconds = int(time.time() - _started_at)`
whenever `_started_at` is truthy. After stopping, `_started_at` still holds the
old value, so uptime appears to keep growing. The snapshot reports incorrect
data.

**Location:** `services/home-miner-daemon/daemon.py:106-113` (stop) and
`daemon.py:135-148` (get_snapshot)

### HIGH: Control serialization not implemented

The ExecPlan requires "control commands must be serialized" and the error taxonomy
defines `ControlCommandConflict`. The daemon has no serialization — only a
threading lock that prevents concurrent in-memory mutations. Two concurrent
HTTP `POST /miner/start` requests can both be processed. No conflict error is
ever raised.

**Location:** `services/home-miner-daemon/daemon.py:186-200`

### MEDIUM: JSONL corruption has no recovery

If `spine.py:_save_event()` crashes mid-write (disk full, process kill, signal),
the JSONL file will have a truncated last line. `_load_events()` calls
`json.loads(line)` on each line — a truncated line raises `JSONDecodeError`,
making the entire spine unreadable. There is no recovery path.

**Location:** `services/home-miner-daemon/spine.py:50-59`

### MEDIUM: File-level race conditions in store

`store.py` performs read-modify-write on `pairing-store.json` without file
locking. Two concurrent `pair_client()` calls could both read the same state,
each write their new pairing, and the second write silently overwrites the first.

**Location:** `services/home-miner-daemon/store.py:72-83`

### MEDIUM: Gateway client hardcodes capabilities and principal

`apps/zend-home-gateway/index.html:626` hardcodes `capabilities: ['observe', 'control']`.
The UI always shows control buttons regardless of actual paired capabilities.

`index.html:781` falls back to a well-known example UUID
(`550e8400-e29b-41d4-a716-446655440000`) for the principal ID.

**Location:** `apps/zend-home-gateway/index.html:626-628` and `781`

### MEDIUM: No event deduplication

Calling the same script twice appends duplicate events with different UUIDs. There
is no idempotency key. Combined with the error taxonomy's `retry append` path,
retry-without-dedup means double writes.

### LOW: Stale snapshot detection is a no-op

The daemon always returns `datetime.now(timezone.utc).isoformat()` as freshness.
There is no freshness threshold. `MinerSnapshotStale` is defined in the taxonomy
but never raised. The client will never display a stale warning because the
daemon always reports "now."

**Location:** `services/home-miner-daemon/daemon.py:147`

### LOW: No CORS headers

The daemon sets no CORS headers. The gateway client makes `fetch()` calls to
`http://127.0.0.1:8080`. If the HTML is served from any origin other than
`127.0.0.1:8080`, browsers will block the requests.

---

## Acceptance Criteria Gap Analysis

| Criterion | Intent | Implementation |
|-----------|--------|-----------------|
| Daemon starts LAN-only | Bind loopback only | Defaults to loopback but `ZEND_BIND_HOST` bypass accepted |
| Pairing creates PrincipalId + capability record | Durable record with token lifecycle | Record created; token is always expired; never checked |
| Status returns MinerSnapshot with freshness | Real timestamp, staleness detectable | Freshness always "now"; uptime grows while stopped |
| Control requires 'control' capability | Enforced at HTTP layer | Only enforced in CLI wrapper; bypassed via HTTP |
| Events append to encrypted spine | Encrypted at rest | Plaintext JSONL; no encryption |
| Inbox shows receipts, alerts, summaries | Derived view of spine | UI has placeholders; no live data flow |
| Gateway proves no local hashing | Audit script with pass/fail | Stub script; no actual inspection logic |
| Trust ceremony | Verification step beyond JSON write | Single `pair_client()` call; no ceremony |
| Serialized control commands | Conflict detection and rejection | No serialization; concurrent requests both process |
| Automated tests | One per error taxonomy case | Zero test files |
| Gateway proof transcripts | `references/gateway-proof.md` with transcripts | File does not exist |
| Onboarding storyboard | `references/onboarding-storyboard.md` | File does not exist |
| Hermes through adapter | Observe-only via contract | Contract written; no live integration |

---

## Remaining Blockers (Ordered by Enforcement Priority)

1. **Daemon HTTP-layer authentication** — every mutating endpoint must validate
   bearer token and capability before processing.
2. **Store/spine consistency** — define which is the authoritative source;
   reconcile writes so they are atomic or the order is guaranteed.
3. **Event spine encryption or correction** — either encrypt events at rest or
   update the spec and docs to stop calling the spine "encrypted."
4. **Token lifecycle** — implement expiration checks and replay detection.
5. **Trust ceremony** — implement a verification step; do not ship pairing as
   "ceremony" when it is a single JSON write.
6. **Control serialization** — detect and reject conflicting commands with
   `ControlCommandConflict`.
7. **`_started_at` reset on stop** — fix the uptime counter.
8. **Bind address validation** — reject `0.0.0.0` and non-loopback addresses in M1.
9. **Automated tests** — zero exist; ExecPlan requires coverage of all error
   taxonomy cases plus trust ceremony, Hermes boundaries, spine routing.
10. **`references/gateway-proof.md`** — required artifact documenting exact
    end-to-end rerun steps and transcripts.
11. **JSONL corruption recovery** — either use atomic writes or detect and
    recover from truncated lines.
12. **Gateway client capability negotiation** — read actual capabilities from
    daemon rather than hardcoding `['observe', 'control']`.

---

## Supervisory Plane Summary

**Milestone 1 scaffold:** Complete. The docs, contracts, directory structure,
and CLI architecture are all in place and match the ExecPlan.

**Milestone 1 enforcement:** Incomplete. The gap between "spec says" and "code
enforces" is too large. The capability model, token lifecycle, trust ceremony,
spine encryption, and control serialization are all documented requirements
that exist in reference files but not in code.

**Recommended next action:** Resolve items 1-8 (authentication through bind
address validation) before attempting automated tests. Items 9-12 can proceed
in parallel once the enforcement layer is in place.

The spec file at `outputs/carried-forward-build-command-center/spec.md` accurately
describes intent. It should not be relaxed — the implementation must be brought
up to meet it.
